"""
Demo Node - Handles guided product demonstrations.
Manages a multi-step workflow to walk users through YouTube features.

OPTIMIZED VERSION:
- LLM-generated responses instead of hardcoded scripts
- User context awareness (knows user's name, role, company)
- Natural conversation during demo
"""
import os
import httpx
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from .state import AgentState
from .nodes import get_llm

# Browser service URL
BROWSER_SERVICE_URL = os.getenv("BROWSER_SERVICE_URL", "http://browser_service:8001")

# LLM instance for demo responses
demo_llm = get_llm()

# Demo persona prompt
DEMO_AGENT_PROMPT = """You are Ravi, a Product Consultant at Keeto, currently giving a live YouTube demo.

**Current Time**: {current_time}

**User Info:**
{user_context}

**Demo Progress:**
- Current Step: {step_name} ({step_number}/6)
- Action Result: {action_result}
- What Just Happened: {step_description}

**Your Task:**
Generate a natural, conversational response that:
1. Briefly explains what just happened in a friendly way (avoid robotic "Step X: Action Y" headers)
2. If the step completed successfully, celebrate briefly
3. If there was an error, acknowledge it gracefully
4. Tell the user what to do next (say "yes" or "next" to continue, or "stop" to exit)

**Important Rules:**
- Do NOT show internal action logs like "Navigating to youtube.com..." or "Typing search query..."
- Be warm and personable, use the user's name naturally
- Keep responses concise (2-4 sentences max)
- If this is the final step (step 6), give a completion message with next steps (book demo, contact sales)

Respond with ONLY your message to the user, nothing else."""

# Demo step definitions (simplified - just actions and metadata)
DEMO_STEPS = {
    0: {
        "name": "intro",
        "description": "Introduction to the demo",
        "action": None,
        "awaits_confirmation": True,
    },
    1: {
        "name": "navigate",
        "description": "Opening YouTube.com in the browser",
        "action": "navigate_youtube",
        "awaits_confirmation": True,
    },
    2: {
        "name": "search_type",
        "description": "Typing 'artificial intelligence' in the search box",
        "action": "type_search",
        "awaits_confirmation": True,
    },
    3: {
        "name": "search_click",
        "description": "Clicking the search button to execute the search",
        "action": "click_search",
        "awaits_confirmation": False,
    },
    4: {
        "name": "select_video",
        "description": "Selecting the first video from the search results",
        "action": "click_video",
        "awaits_confirmation": True,
    },
    5: {
        "name": "pause_video",
        "description": "Pausing the video to demonstrate playback controls",
        "action": "pause_video",
        "awaits_confirmation": False,
    },
    6: {
        "name": "complete",
        "description": "Demo completed successfully",
        "action": None,
        "awaits_confirmation": False,
    },
}


def _call_browser_service(endpoint: str, data: dict = None, method: str = "POST") -> dict:
    """Make HTTP call to browser service."""
    try:
        with httpx.Client(timeout=30.0) as client:
            if method == "GET":
                response = client.get(f"{BROWSER_SERVICE_URL}/{endpoint}")
            else:
                response = client.post(f"{BROWSER_SERVICE_URL}/{endpoint}", json=data or {})
            return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _execute_demo_action(action: str, state: AgentState) -> str:
    """Execute a browser action for the demo."""
    
    if action == "navigate_youtube":
        result = _call_browser_service("navigate", {"url": "https://www.youtube.com"})
        if result.get("success"):
            return "Successfully opened YouTube"
        return f"Navigation issue: {result.get('error', 'unknown')}"
    
    elif action == "type_search":
        result = _call_browser_service("type", {
            "selector": "input[name='search_query']",
            "text": "artificial intelligence"
        })
        if result.get("success"):
            return "Successfully typed 'artificial intelligence' in the search box"
        return f"Typing issue: {result.get('error', 'unknown')}"
    
    elif action == "click_search":
        # Try pressing Enter in the search box instead of clicking the button
        result = _call_browser_service("type", {
            "selector": "input[name='search_query']",
            "text": "\n"  # Press Enter
        })
        if result.get("success"):
            return "Successfully executed the search"
        # Fallback: try clicking the button
        result = _call_browser_service("click", {"selector": "button#search-icon-legacy"})
        if result.get("success"):
            return "Successfully clicked search button"
        return f"Search issue: {result.get('error', 'unknown')}"
    
    elif action == "click_video":
        result = _call_browser_service("click", {
            "selector": "ytd-video-renderer a#video-title"
        })
        if result.get("success"):
            return "Successfully selected a video"
        return f"Video selection issue: {result.get('error', 'unknown')}"
    
    elif action == "pause_video":
        result = _call_browser_service("click", {"selector": "video.html5-main-video"})
        if result.get("success"):
            return "Successfully toggled playback"
        result = _call_browser_service("click", {"selector": "button.ytp-play-button"})
        if result.get("success"):
            return "Successfully clicked play/pause button"
        return f"Pause issue: {result.get('error', 'unknown')}"
    
    return "Unknown action"


def _generate_demo_response(step_info: dict, step_number: int, action_result: str, user_context: dict) -> str:
    """Use LLM to generate a natural response for the demo step."""
    from datetime import datetime
    import pytz
    
    # Get current time
    ist = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(ist).strftime("%A, %B %d, %Y at %I:%M %p IST")
    
    # Build user context string
    context_str = "Unknown user"
    if user_context:
        name = user_context.get("name", "")
        company = user_context.get("company", "")
        role = user_context.get("role", "")
        if name:
            context_str = f"Name: {name}"
            if role:
                context_str += f", Role: {role}"
            if company:
                context_str += f", Company: {company}"
    
    # Special case for intro step
    if step_number == 0:
        return f"""🎬 **Welcome to the YouTube Demo!**

Hi {user_context.get('name', 'there') if user_context else 'there'}! I'm Ravi, and I'll be your guide today.

I'm going to show you how our AI agent can interact with YouTube by:
1. **Searching** for "artificial intelligence" videos
2. **Selecting** a video from the results
3. **Controlling** playback

Ready to start? Just say **"yes"** or **"start"** when you're ready!"""
    
    # Special case for completion step
    if step_number == 6:
        return f"""✅ **Demo Complete!**

Great job following along, {user_context.get('name', 'there') if user_context else 'there'}! You've just seen our AI agent:
- Navigate to YouTube
- Search for content
- Select and control video playback

**Interested in having this capability for YOUR product?**

📞 Book a demo with our sales team: **+1-555-0199**
📧 Or email us at: **sales@keeto.ai**

Is there anything else you'd like to know about Keeto?"""
    
    # Use LLM for other steps
    prompt = ChatPromptTemplate.from_messages([
        ("system", DEMO_AGENT_PROMPT.format(
            current_time=current_time,
            user_context=context_str,
            step_name=step_info["name"],
            step_number=step_number,
            action_result=action_result,
            step_description=step_info["description"],
        )),
        ("human", "Generate your response to the user.")
    ])
    
    chain = prompt | demo_llm
    
    try:
        result = chain.invoke({})
        return result.content
    except Exception as e:
        # Fallback to simple message
        return f"Done with step {step_number}. Say 'yes' or 'next' to continue."


def demo_node(state: AgentState) -> dict:
    """
    Handles the guided demo workflow.
    Uses LLM for natural responses and user context awareness.
    """
    messages = state.get("messages", [])
    demo = state.get("demo") or {}
    user_context = state.get("user_context", {})
    
    # Get user's name for personalization
    user_name = user_context.get("name", "there") if user_context else "there"
    
    # Initialize demo if not active
    if not demo.get("is_active"):
        print("🎬 Initializing demo workflow")
        step_info = DEMO_STEPS[0]
        response = _generate_demo_response(step_info, 0, "", user_context)
        return {
            "messages": [AIMessage(content=response)],
            "demo": {
                "is_active": True,
                "step": 0,
                "target_site": "youtube",
                "awaiting_confirmation": True,
            }
        }
    
    # Get current step
    current_step = demo.get("step", 0)
    awaiting = demo.get("awaiting_confirmation", False)
    
    # Check user input
    if awaiting and messages:
        last_message = messages[-1]
        if isinstance(last_message, HumanMessage):
            user_text = last_message.content.lower()
            confirmations = ["yes", "yeah", "yep", "ok", "okay", "sure", "start", "go", "continue", "next"]
            
            if any(conf in user_text for conf in confirmations):
                current_step += 1
                awaiting = False
            elif any(word in user_text for word in ["no", "stop", "cancel", "exit", "quit"]):
                return {
                    "messages": [AIMessage(content=f"No problem, {user_name}! Demo cancelled. Feel free to ask me anything else or request another demo anytime.")],
                    "demo": {"is_active": False, "step": 0, "target_site": "", "awaiting_confirmation": False}
                }
            else:
                # For any other input during demo, try to handle it conversationally
                return {
                    "messages": [AIMessage(content=f"I'm currently in demo mode, {user_name}. Say **\"yes\"** to continue to the next step, or **\"stop\"** if you'd like to exit the demo and chat.")],
                    "demo": demo
                }
    
    # Get step info
    step_info = DEMO_STEPS.get(current_step, DEMO_STEPS[6])
    
    # Execute action if this step has one
    action_result = ""
    if step_info.get("action"):
        action_result = _execute_demo_action(step_info["action"], state)
        print(f"🎬 Demo action '{step_info['action']}': {action_result}")
    
    # Generate natural response using LLM
    response = _generate_demo_response(step_info, current_step, action_result, user_context)
    
    # Update demo state
    new_demo = {
        "is_active": current_step < 6,
        "step": current_step if step_info.get("awaits_confirmation") else current_step + 1,
        "target_site": "youtube",
        "awaiting_confirmation": step_info.get("awaits_confirmation", False),
    }
    
    if current_step >= 6:
        new_demo["is_active"] = False
    
    return {
        "messages": [AIMessage(content=response)],
        "demo": new_demo
    }
