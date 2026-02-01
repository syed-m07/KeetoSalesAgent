"""
Graph Node Definitions.
Each node is a function that takes AgentState and returns a partial update.
"""
import os
from typing import Literal
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .state import AgentState

# --- LLM Configuration ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")


def get_llm():
    """Initialize LLM based on provider configuration."""
    if LLM_PROVIDER == "groq" and GROQ_API_KEY:
        from langchain_groq import ChatGroq
        return ChatGroq(
            api_key=GROQ_API_KEY,
            model_name=GROQ_MODEL,
            temperature=0.3,
        )
    else:
        from langchain_community.chat_models import ChatOllama
        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            temperature=0.3,
        )


# Initialize shared LLM
llm = get_llm()


# --- System Prompts ---
ROUTER_SYSTEM_PROMPT = """You are an intent classifier for a Sales AI Agent.

Analyze the user's message and classify their intent into ONE of these categories:
- "navigate": User wants to go somewhere on web, click something, or interact with a page
- "enrich": User wants information about a company, person, or wants research done
- "crm": User wants to save, list, or manage leads/contacts
- "chat": General conversation, greetings, questions about capabilities

Respond with ONLY the category name, nothing else."""


CHAT_SYSTEM_PROMPT = """You are Ravi, a Product Consultant at Keeto.
Your role is to guide product demonstrations and help qualify prospects for sales calls.

{user_context}

Your goals:
1. Answer questions about Keeto's product/services clearly
2. Understand the prospect's needs and pain points
3. Guide them toward booking a demo call with our sales team
4. Be helpful, professional, and consultative (never pushy)

Important:
- Always introduce yourself as "Ravi from Keeto" when greeting users
- Never use placeholder text like [Company Name] - always say "Keeto"
- If the user asks about browsing, remind them they can ask you to "go to [website]"

{previous_conversation_context}"""



# --- Node Functions ---

def router_node(state: AgentState) -> dict:
    """
    Classifies user intent and sets next_action.
    This is the entry point after user input.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"next_action": "chat"}
    
    last_message = messages[-1]
    if not isinstance(last_message, HumanMessage):
        return {"next_action": "chat"}
    
    # Create classification prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", ROUTER_SYSTEM_PROMPT),
        ("human", "{input}")
    ])
    
    chain = prompt | llm
    
    try:
        result = chain.invoke({"input": last_message.content})
        intent = result.content.strip().lower()
        
        # Validate intent
        valid_intents = ["navigate", "enrich", "crm", "chat"]
        if intent not in valid_intents:
            intent = "chat"
        
        print(f"🧭 Router classified intent: {intent}")
        return {"next_action": intent}
    
    except Exception as e:
        print(f"Router error: {e}")
        return {"next_action": "chat"}


def chat_node(state: AgentState) -> dict:
    """
    Handles general conversation and greetings.
    """
    messages = state.get("messages", [])
    user_context = state.get("user_context", {})
    
    # Build context string
    context_str = ""
    if user_context:
        name = user_context.get("name", "")
        company = user_context.get("company", "")
        role = user_context.get("role", "")
        if name or company or role:
            context_str = f"You are speaking with {name or 'a user'}"
            if role:
                context_str += f", a {role}"
            if company:
                context_str += f" at {company}"
            context_str += "."
    
    # Build previous conversation context
    prev_context = ""
    if user_context:
        last_summary = user_context.get("last_conversation_summary", "")
        if last_summary:
            prev_context = f"\n\nPrevious conversation summary: {last_summary}\nIf this is a returning user, offer to recap the previous discussion."
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", CHAT_SYSTEM_PROMPT.format(
            user_context=context_str,
            previous_conversation_context=prev_context
        )),
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    chain = prompt | llm
    
    try:
        result = chain.invoke({"messages": messages})
        return {"messages": [AIMessage(content=result.content)]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"I encountered an error: {e}")]}


def route_by_intent(state: AgentState) -> Literal["navigate", "enrich", "crm", "chat"]:
    """
    Conditional edge function that routes based on next_action.
    """
    next_action = state.get("next_action", "chat")
    if next_action in ["navigate", "enrich", "crm", "chat"]:
        return next_action
    return "chat"
