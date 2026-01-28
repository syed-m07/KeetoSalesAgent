"""
Conversational AI Agent with Tool Use.
Supports both Ollama (local) and Groq (cloud) LLM providers.
Switch via LLM_PROVIDER environment variable.
"""
import os
from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.prompts import PromptTemplate

from .tools import browser_tools
from .enrichment_tools import enrichment_tools
from .crm_tools import crm_tools

# --- Configuration from Environment ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()  # "ollama" or "groq"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
ENRICHMENT_SERVICE_URL = os.getenv("ENRICHMENT_SERVICE_URL", "http://enrichment_service:8002")


def get_llm():
    """Initialize LLM based on provider configuration."""
    if LLM_PROVIDER == "groq" and GROQ_API_KEY:
        print(f"🚀 Using Groq API with model: {GROQ_MODEL}")
        from langchain_groq import ChatGroq
        return ChatGroq(
            api_key=GROQ_API_KEY,
            model_name=GROQ_MODEL,
            temperature=0.2,
        )
    else:
        print(f"🦙 Using Ollama with model: {OLLAMA_MODEL}")
        from langchain_community.chat_models import ChatOllama
        return ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_HOST,
            temperature=0.2,
        )


# Initialize the LLM
llm = get_llm()

# Conversation memory - keep last 5 exchanges (Groq is fast, can handle more)
memory = ConversationBufferWindowMemory(
    memory_key="chat_history",
    k=5,
    return_messages=False,
)

# --- ReAct Prompt ---
REACT_PROMPT = PromptTemplate.from_template("""You are a helpful AI sales agent. You can browse the web using tools.

Tools available:
{tools}

Tool names: {tool_names}

RESPONSE FORMAT:
For simple questions (greetings), respond DIRECTLY:
Thought: This is a greeting, no tools needed.
Final Answer: Hello! How can I help you today?

For web tasks, use ONE tool then STOP:
Thought: I need to [action].
Action: [tool name]
Action Input: [input]
Observation: [result]
Thought: Done. I should tell the user.
Final Answer: [describe what you did]

CRITICAL RULES:
1. After typing text → immediately say "I typed [text] in the search field."
2. After navigating → immediately say "I navigated to [site]."
3. NEVER use get_page_text after typing or navigating
4. ONE tool per request, then Final Answer
5. If tool succeeded, DO NOT call more tools

Chat History: {chat_history}

Question: {input}
{agent_scratchpad}""")

# Combine all tools
all_tools = browser_tools + enrichment_tools + crm_tools

# Create the ReAct agent
agent = create_react_agent(
    llm=llm,
    tools=all_tools,
    prompt=REACT_PROMPT,
)

# Create the agent executor - faster timeout for Groq, longer for Ollama
timeout = 60 if LLM_PROVIDER == "groq" else 300

agent_executor = AgentExecutor(
    agent=agent,
    tools=all_tools,
    memory=memory,
    verbose=True,
    handle_parsing_errors="Give Final Answer now with what you know.",
    max_iterations=3,  # Reduced to prevent looping - 1 tool call + 2 attempts
    max_execution_time=timeout,
    return_intermediate_steps=True,  # Helps with debugging
)


def get_agent_response(user_input: str) -> str:
    """
    Gets a response from the conversational agent.
    
    Args:
        user_input: The text from the user.
        
    Returns:
        The agent's response.
    """
    try:
        result = agent_executor.invoke({"input": user_input})
        output = result.get("output", "")
        
        # If output is empty or just "Agent stopped", try to get info from steps
        if not output or "stopped" in output.lower() or output.strip() == "":
            steps = result.get("intermediate_steps", [])
            if steps:
                # Get the last successful action result
                last_action, last_result = steps[-1]
                action_name = last_action.tool
                result_str = str(last_result)
                
                # Return meaningful response based on tool and its actual result
                if action_name == "type_text":
                    return "Done! I typed your text in the search field."
                elif action_name == "navigate_browser":
                    return "I navigated to the page."
                elif action_name == "click_element":
                    if "success" in result_str.lower():
                        return "Done! I clicked the button. The page may be loading new content."
                    return f"I tried to click but: {result_str[:200]}"
                elif action_name == "get_page_text":
                    # Extract actual page content and return it
                    if "[IMPORTANT" in result_str:
                        # Remove our stop instruction from the output
                        clean_result = result_str.split("[IMPORTANT")[0].strip()
                    else:
                        clean_result = result_str
                    if len(clean_result) > 500:
                        clean_result = clean_result[:500] + "..."
                    return f"Here's what I see on the page:\n\n{clean_result}"
                elif action_name == "get_page_info":
                    return f"Current page: {result_str}"
                else:
                    # Return the actual result, not just action name
                    if len(result_str) > 300:
                        result_str = result_str[:300] + "..."
                    return result_str
            return "I processed your request but couldn't generate a response."
        
        return output
        
    except Exception as e:
        error_msg = str(e)
        if "iteration limit" in error_msg.lower() or "time limit" in error_msg.lower():
            return "Done! I completed the action you requested."
        return f"I encountered an error: {error_msg}. Please try rephrasing your question."
