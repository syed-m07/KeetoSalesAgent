"""
Conversational AI Agent with Tool Use.
Uses LangChain with Ollama LLM and Browser Tools.
Optimized for smaller models (llama3.2:3b).
"""
import os
from langchain_community.chat_models import ChatOllama
from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.prompts import PromptTemplate

from .tools import browser_tools

# --- Configuration from Environment ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# Initialize the LLM pointing to the Ollama container
llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_HOST,
    temperature=0.2,  # Lower temperature for more predictable output
)

# Conversation memory - keep last 3 exchanges to reduce context bloat
memory = ConversationBufferWindowMemory(
    memory_key="chat_history",
    k=3,
    return_messages=False,  # Return as string, easier for small models
)

# --- Simplified ReAct Prompt for Small Models ---
REACT_PROMPT = PromptTemplate.from_template("""You are a helpful AI assistant that can browse the web.

Tools available:
{tools}

Tool names: {tool_names}

FORMAT (follow exactly):
Question: <user question>
Thought: <think about what to do>
Action: <tool name from [{tool_names}]>
Action Input: <input for the tool>
Observation: <tool result>
Thought: I have the answer
Final Answer: <your response to the user>

IMPORTANT RULES:
- Use navigate_browser with just the URL like: google.com
- After getting a result, give Final Answer immediately
- Do NOT repeat the same action
- If you don't need a tool, skip to Final Answer

Chat History: {chat_history}

Question: {input}
{agent_scratchpad}""")

# Create the ReAct agent
agent = create_react_agent(
    llm=llm,
    tools=browser_tools,
    prompt=REACT_PROMPT,
)

# Create the agent executor with higher tolerance
agent_executor = AgentExecutor(
    agent=agent,
    tools=browser_tools,
    memory=memory,
    verbose=True,
    handle_parsing_errors="Check your output format. Use 'Final Answer:' to respond.",
    max_iterations=10,  # Increased for complex tasks
    max_execution_time=300,  # 5 minute timeout for slow hardware
)


def get_agent_response(user_input: str) -> str:
    """
    Gets a response from the conversational agent.
    The agent can use browser tools to interact with websites.
    
    Args:
        user_input: The text from the user.
        
    Returns:
        The agent's response.
    """
    try:
        result = agent_executor.invoke({"input": user_input})
        output = result.get("output", "")
        
        # Handle empty or error outputs
        if not output or output.strip() == "":
            return "I processed your request but couldn't generate a response. Please try again."
        
        return output
        
    except Exception as e:
        error_msg = str(e)
        # Provide helpful fallback for common errors
        if "iteration limit" in error_msg.lower() or "time limit" in error_msg.lower():
            return "I took too long processing that request. Try asking something simpler, like 'go to google.com'."
        return f"I encountered an error: {error_msg}. Please try rephrasing your question."
