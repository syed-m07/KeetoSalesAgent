"""
Demo Node - Handles guided product demonstrations.
Manages a multi-step workflow to walk users through YouTube features.
"""
import os
import httpx
from langchain_core.messages import AIMessage, HumanMessage

from .state import AgentState

# Browser service URL
BROWSER_SERVICE_URL = os.getenv("BROWSER_SERVICE_URL", "http://browser_service:8001")

# Demo step definitions
DEMO_STEPS = {
    0: {
        "name": "intro",
        "message": """🎬 **Welcome to the YouTube Demo!**

I'm Ravi, and I'll be your guide today. I'm going to show you how YouTube works by:

1. **Searching** for "artificial intelligence" videos
2. **Selecting** a video from the results
3. **Controlling** playback (pause/play)

Are you ready to start? Just say **"yes"** or **"start"** when you're ready!""",
        "action": None,
        "awaits_confirmation": True,
    },
    1: {
        "name": "navigate",
        "message": """🌐 **Step 1: Navigating to YouTube**

I'm now opening YouTube.com in the browser. Watch the browser window on the **left side** of your screen...

*Navigating to youtube.com...*""",
        "action": "navigate_youtube",
        "awaits_confirmation": True,  # Wait for user before continuing
    },
    2: {
        "name": "search_type",
        "message": """🔍 **Step 2: Using the Search Feature**

Now I'll type "artificial intelligence" in the search box to demonstrate YouTube's powerful search capability.

*Typing search query...*

Do you see the search box being filled? Say **"yes"** to continue.""",
        "action": "type_search",
        "awaits_confirmation": True,
    },
    3: {
        "name": "search_click",
        "message": """🖱️ **Step 3: Executing the Search**

I'm clicking the search button to find AI-related videos.

*Clicking search...*

Watch as the results load!""",
        "action": "click_search",
        "awaits_confirmation": False,
    },
    4: {
        "name": "select_video",
        "message": """📺 **Step 4: Selecting a Video**

Now I'll identify and click on the first organic (non-sponsored) video result.

*Analyzing results and selecting a video...*

Are you following along? Say **"yes"** to continue.""",
        "action": "click_video",
        "awaits_confirmation": True,
    },
    5: {
        "name": "pause_video",
        "message": """⏸️ **Step 5: Playback Control**

The video is now playing. I'll demonstrate control by clicking the pause button.

*Pausing the video...*""",
        "action": "pause_video",
        "awaits_confirmation": False,
    },
    6: {
        "name": "complete",
        "message": """✅ **Demo Complete!**

That concludes our YouTube demonstration! You've seen:
- ✓ Navigation to the platform
- ✓ Search functionality
- ✓ Video selection
- ✓ Playback controls

**Interested in having this capability for YOUR product?**

📞 Book a demo with our sales team: **+1-555-0199**
📧 Or email us at: **sales@keeto.ai**

Is there anything else you'd like me to demonstrate or any questions about Keeto?""",
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
            return "✅ Navigated to YouTube successfully!"
        return f"⚠️ Navigation issue: {result.get('error', 'unknown')}"
    
    elif action == "type_search":
        result = _call_browser_service("type", {
            "selector": "input[name='search_query']",
            "text": "artificial intelligence"
        })
        if result.get("success"):
            return "✅ Typed 'artificial intelligence' in search box!"
        return f"⚠️ Typing issue: {result.get('error', 'unknown')}"
    
    elif action == "click_search":
        # Try pressing Enter in the search box instead of clicking the button
        # This is more reliable across YouTube versions
        result = _call_browser_service("type", {
            "selector": "input[name='search_query']",
            "text": "\n"  # Press Enter
        })
        if result.get("success"):
            return "✅ Executed search (pressed Enter)!"
        # Fallback: try clicking the button
        result = _call_browser_service("click", {"selector": "button#search-icon-legacy"})
        if result.get("success"):
            return "✅ Clicked search button!"
        return f"⚠️ Search issue: {result.get('error', 'unknown')}"
    
    elif action == "click_video":
        # Try to click first video result (not ad)
        # YouTube uses ytd-video-renderer for regular videos
        result = _call_browser_service("click", {
            "selector": "ytd-video-renderer a#video-title"
        })
        if result.get("success"):
            return "✅ Selected a video!"
        return f"⚠️ Video selection issue: {result.get('error', 'unknown')}"
    
    elif action == "pause_video":
        # Click on video player to pause
        result = _call_browser_service("click", {"selector": "video.html5-main-video"})
        if result.get("success"):
            return "✅ Toggled video playback!"
        # Fallback: try the pause button
        result = _call_browser_service("click", {"selector": "button.ytp-play-button"})
        if result.get("success"):
            return "✅ Clicked play/pause button!"
        return f"⚠️ Pause issue: {result.get('error', 'unknown')}"
    
    return "Unknown action"


def demo_node(state: AgentState) -> dict:
    """
    Handles the guided demo workflow.
    Manages step progression based on user confirmation.
    """
    messages = state.get("messages", [])
    demo = state.get("demo") or {}
    user_context = state.get("user_context", {})
    
    # Get user's name for personalization
    user_name = user_context.get("name", "there") if user_context else "there"
    
    # Check if user is asking to restart demo (explicit demo request while demo is active)
    if messages:
        last_message = messages[-1]
        if isinstance(last_message, HumanMessage):
            user_text = last_message.content.lower()
            demo_triggers = ["demo", "show me", "demonstrate", "walkthrough", "tutorial", "guide me", "start over", "restart"]
            if any(trigger in user_text for trigger in demo_triggers):
                print("🎬 Demo restart requested - resetting to step 0")
                demo = {}  # Force reset
    
    # Initialize demo if not active (first time entering demo mode or reset)
    # On first entry, immediately show intro and set up for next turn
    if not demo.get("is_active"):
        print("🎬 Initializing demo workflow - showing intro")
        # Return intro message and initialize state
        step_info = DEMO_STEPS[0]  # Intro step
        return {
            "messages": [AIMessage(content=step_info["message"])],
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
    
    # Check if user confirmed (for steps that need it)
    if awaiting and messages:
        last_message = messages[-1]
        if isinstance(last_message, HumanMessage):
            user_text = last_message.content.lower()
            confirmations = ["yes", "yeah", "yep", "ok", "okay", "sure", "start", "go", "continue", "next"]
            
            if any(conf in user_text for conf in confirmations):
                # User confirmed, move to next step
                current_step += 1
                awaiting = False
            elif any(word in user_text for word in ["no", "stop", "cancel", "exit", "quit"]):
                # User wants to exit demo
                return {
                    "messages": [AIMessage(content=f"No problem, {user_name}! Demo cancelled. Feel free to ask me anything else about Keeto or request another demo anytime.")],
                    "demo": {"is_active": False, "step": 0, "target_site": "", "awaiting_confirmation": False}
                }
            else:
                # Unclear response, ask again
                return {
                    "messages": [AIMessage(content=f"I didn't quite catch that, {user_name}. Just say **\"yes\"** to continue with the demo, or **\"stop\"** to exit.")],
                    "demo": demo  # Keep same state
                }
    
    # Get step info
    step_info = DEMO_STEPS.get(current_step, DEMO_STEPS[6])  # Default to complete
    
    # Execute action if this step has one
    action_result = ""
    if step_info.get("action"):
        action_result = _execute_demo_action(step_info["action"], state)
        print(f"🎬 Demo action '{step_info['action']}': {action_result}")
    
    # Build response message
    response_message = step_info["message"]
    if action_result:
        response_message += f"\n\n{action_result}"
    
    # Add follow-up prompt if this step awaits confirmation
    if step_info.get("awaits_confirmation"):
        response_message += "\n\nSay **\"yes\"** or **\"next\"** to continue to the next step."
    
    # Personalize with user name
    response_message = response_message.replace("Ravi", f"Ravi (for {user_name})")
    
    # Update demo state
    new_demo = {
        "is_active": current_step < 6,  # Deactivate after step 6 (complete)
        "step": current_step if step_info.get("awaits_confirmation") else current_step + 1,
        "target_site": "youtube",
        "awaiting_confirmation": step_info.get("awaits_confirmation", False),
    }
    
    # If we just completed step 6, mark demo as complete
    if current_step >= 6:
        new_demo["is_active"] = False
    
    return {
        "messages": [AIMessage(content=response_message)],
        "demo": new_demo
    }
