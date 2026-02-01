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
# Priority: Gemini > Groq > Ollama
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")  # Smarter model (free on Groq)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()  # Default to groq


def get_llm():
    """
    Initialize LLM based on provider configuration.
    Respects LLM_PROVIDER env var strictly.
    """
    # Use Groq if provider is groq (default, free, fast)
    if LLM_PROVIDER == "groq" and GROQ_API_KEY:
        from langchain_groq import ChatGroq
        print(f"🚀 Using Groq with model: {GROQ_MODEL}")
        return ChatGroq(
            api_key=GROQ_API_KEY,
            model_name=GROQ_MODEL,
            temperature=0.3,
            timeout=60,
        )
    
    # Use Gemini if explicitly set
    if LLM_PROVIDER in ["gemini", "google"] and GEMINI_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            print("🧠 Using Gemini 2.0 Flash")
            return ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=GEMINI_API_KEY,
                temperature=0.3,
                max_output_tokens=2048,
                timeout=120,
            )
        except Exception as e:
            print(f"⚠️ Gemini init failed: {e}, falling back to Groq")
            if GROQ_API_KEY:
                from langchain_groq import ChatGroq
                return ChatGroq(api_key=GROQ_API_KEY, model_name=GROQ_MODEL, temperature=0.3)
    
    # Last resort: Ollama
    from langchain_community.chat_models import ChatOllama
    print("🦙 Using Ollama (local)")
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

**Current Time**: {current_time}

**About You:**
You are a professional, consultative sales agent. Your role is to understand prospects' needs and guide them toward a solution.

**About Keeto:**
Keeto is an AI-powered Sales Agent platform with:
- **Intelligent Browser Automation**: Uses Playwright to navigate websites, extract data, and interact with pages autonomously
- **Voice Capabilities**: Natural text-to-speech for lifelike conversations
- **Premium Glassmorphism UI**: Modern, beautiful dark-themed interface
- **24/7 Availability**: Works around the clock to qualify leads and book demos
- **LangGraph Multi-Agent System**: Advanced reasoning and routing for complex tasks

{user_context}

**Your Sales Methodology (Consultative Selling):**
1. **Build Rapport**: Greet warmly and establish trust
2. **Discover Needs**: Ask questions to understand:
   - Their current challenges (Pain Points)
   - What they're trying to accomplish (Goals)
   - Their timeline (Urgency)
   - Who's involved in decisions (Authority)
3. **Present Value**: Connect Keeto's features to THEIR specific needs
4. **Guide to Action**: Suggest booking a demo or trying the product

**Important Guidelines:**
- ALWAYS introduce yourself as "Ravi from Keeto" when greeting new users
- Be conversational, not robotic - use natural language
- Ask ONE follow-up question at a time to uncover needs
- Listen more than you talk - focus on THEIR problems
- Never be pushy - be helpful and consultative
- If asked about time, use the Current Time provided above
- If asked what you remember, reference the conversation history naturally

{previous_conversation_context}

**Your Goal:** Help prospects understand if Keeto is a fit for them, and guide qualified leads toward booking a demo."""



# --- Node Functions ---

def router_node(state: AgentState) -> dict:
    """
    Classifies user intent and sets next_action.
    This is the entry point after user input.
    
    Special handling:
    - If demo is active, continue to demo node
    - If user asks for demo, start demo mode
    """
    messages = state.get("messages", [])
    demo = state.get("demo", {})
    
    # If demo is active, always route to demo node
    if demo and demo.get("is_active"):
        print("🎬 Demo active - routing to demo_node")
        return {"next_action": "demo"}
    
    if not messages:
        return {"next_action": "chat"}
    
    last_message = messages[-1]
    if not isinstance(last_message, HumanMessage):
        return {"next_action": "chat"}
    
    user_text = last_message.content.lower()
    
    # Quick pattern matching for demo requests (avoid LLM call)
    # If user explicitly asks for demo, always restart from beginning
    demo_triggers = ["demo", "show me", "demonstrate", "walkthrough", "tutorial", "guide me"]
    if any(trigger in user_text for trigger in demo_triggers):
        print("🎬 Demo request detected - resetting and routing to demo_node")
        # Reset demo state to force restart from step 0
        return {
            "next_action": "demo",
            "demo": None  # Reset so demo_node initializes fresh
        }
    
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
    from datetime import datetime
    import pytz
    
    messages = state.get("messages", [])
    user_context = state.get("user_context", {})
    
    # Get current time in IST
    ist = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(ist).strftime("%A, %B %d, %Y at %I:%M %p IST")
    
    # Build context string
    context_str = ""
    if user_context:
        name = user_context.get("name", "")
        company = user_context.get("company", "")
        role = user_context.get("role", "")
        if name or company or role:
            context_str = f"**Who You're Speaking With:**\nYou are currently speaking with {name or 'a user'}"
            if role:
                context_str += f", who is a {role}"
            if company:
                context_str += f" at {company}"
            context_str += "."
    
    # Build previous conversation context
    prev_context = ""
    if user_context:
        last_summary = user_context.get("last_conversation_summary", "")
        if last_summary:
            prev_context = f"\n\n**Previous Conversation:**\n{last_summary}\n(If the user asks if you remember them or your previous conversation, reference this naturally.)"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", CHAT_SYSTEM_PROMPT.format(
            current_time=current_time,
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


def route_by_intent(state: AgentState) -> Literal["navigate", "enrich", "crm", "chat", "demo"]:
    """
    Conditional edge function that routes based on next_action.
    """
    next_action = state.get("next_action", "chat")
    if next_action in ["navigate", "enrich", "crm", "chat", "demo"]:
        return next_action
    return "chat"
