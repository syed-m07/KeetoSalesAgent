"""
Demo Node - Handles guided product demonstrations.
Manages a multi-step workflow to walk users through YouTube features.

FINAL OPTIMIZED VERSION:
- Split Brain: Short voice scripts for TTS, detailed chat for display
- Smart Retry: Retries failed actions before skipping
- Robust Selectors: Multiple fallback strategies for YouTube
"""
import os
import time
import httpx
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from .state import AgentState
from .nodes import get_llm

# Browser service URL
BROWSER_SERVICE_URL = os.getenv("BROWSER_SERVICE_URL", "http://browser_service:8001")

# LLM instance for demo responses
demo_llm = get_llm()

# Demo persona prompt (for chat display only)
DEMO_AGENT_PROMPT = """You are Ravi, a Product Consultant at Keeto, currently giving a live YouTube demo.

**User Info:** {user_context}

**Demo Progress:**
- Current Step: {step_name} ({step_number}/6)
- Action Result: {action_result}
- What Just Happened: {step_description}

**Your Task:**
Generate a natural, conversational response (2-3 sentences max) that:
1. Briefly explains what just happened
2. Tells the user to say "next" to continue

Respond with ONLY your message to the user."""

# Demo step definitions with voice scripts
DEMO_STEPS = {
    0: {
        "name": "intro",
        "description": "Introduction to the demo",
        "action": None,
        "awaits_confirmation": True,
        "voice_script": "Welcome! I'm Ravi, your guide. Say 'start' when ready.",
    },
    1: {
        "name": "navigate",
        "description": "Opening YouTube.com in the browser",
        "action": "navigate_youtube",
        "awaits_confirmation": True,
        "voice_script": "Opening YouTube now. Say 'next' to continue.",
    },
    2: {
        "name": "search_type",
        "description": "Typing 'artificial intelligence' in the search box",
        "action": "type_search",
        "awaits_confirmation": True,
        "voice_script": "Searching for AI videos. Say 'next' when ready.",
    },
    3: {
        "name": "search_click",
        "description": "Executing the search",
        "action": "click_search",
        "awaits_confirmation": False,
        "voice_script": "Here are the search results.",
    },
    4: {
        "name": "select_video",
        "description": "Selecting the first video from the search results",
        "action": "click_video",
        "awaits_confirmation": True,
        "voice_script": "Playing the first video. Say 'next' to continue.",
    },
    5: {
        "name": "pause_video",
        "description": "Pausing the video to demonstrate playback controls",
        "action": "pause_video",
        "awaits_confirmation": False,
        "voice_script": "Paused the video.",
    },
    6: {
        "name": "complete",
        "description": "Demo completed successfully",
        "action": None,
        "awaits_confirmation": False,
        "voice_script": "Demo complete! Contact sales at keeto.ai for more.",
    },
}


def _call_browser_service(endpoint: str, data: dict = None, method: str = "POST", timeout: float = 30.0) -> dict:
    """Make HTTP call to browser service with extended timeout."""
    try:
        with httpx.Client(timeout=timeout) as client:
            if method == "GET":
                response = client.get(f"{BROWSER_SERVICE_URL}/{endpoint}")
            else:
                response = client.post(f"{BROWSER_SERVICE_URL}/{endpoint}", json=data or {})
            return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _get_video_state() -> dict:
    """Get current video element state from browser."""
    result = _call_browser_service("get-video-state", method="GET")
    if result.get("success") and result.get("data"):
        return result["data"].get("data", {})
    return {"exists": False}


def _handle_interrupt_command(user_text: str, user_name: str) -> dict | None:
    """Handle user commands that should interrupt the demo flow."""
    user_text_lower = user_text.lower()
    
    # Pause command
    if any(word in user_text_lower for word in ["pause", "stop video", "pause video", "hold"]):
        video_state = _get_video_state()
        if video_state.get("exists"):
            if not video_state.get("paused", True):
                # Video is playing, pause it using K shortcut
                _call_browser_service("press", {"key": "k"})
                time.sleep(0.5)
                new_state = _get_video_state()
                if new_state.get("paused", False):
                    return {
                        "text": f"Done, {user_name}! I've paused the video. Say **'next'** to continue the demo or **'play'** to resume.",
                        "voice": "Video paused."
                    }
                return {
                    "text": f"I tried to pause but it didn't work. The video might still be loading.",
                    "voice": "Couldn't pause right now."
                }
            else:
                return {
                    "text": f"The video is already paused, {user_name}.",
                    "voice": "Already paused."
                }
        return {
            "text": "There's no video playing right now.",
            "voice": "No video playing."
        }
    
    # Play/resume command
    if any(word in user_text_lower for word in ["play", "resume", "unpause", "continue video"]):
        video_state = _get_video_state()
        if video_state.get("exists") and video_state.get("paused", True):
            _call_browser_service("press", {"key": "k"})
            return {
                "text": f"Resuming the video, {user_name}! Say **'next'** when you're ready to continue the demo.",
                "voice": "Video playing."
            }
    
    return None  # Not an interrupt command


def _execute_demo_action(action: str, state: AgentState, retry_attempt: int = 0) -> str:
    """Execute a browser action for the demo with robust selectors."""
    
    if action == "navigate_youtube":
        result = _call_browser_service("navigate", {"url": "https://www.youtube.com", "wait_until": "networkidle"}, timeout=45.0)
        if result.get("success"):
            time.sleep(2)  # Wait for YouTube dynamic content
            return "Successfully opened YouTube"
        return f"Navigation issue: {result.get('error', 'unknown')}"
    
    elif action == "type_search":
        # Wait for search box to be ready, then type
        result = _call_browser_service("type", {
            "selector": "input#search",  # YouTube's main search input
            "text": "artificial intelligence",
            "timeout": 10000
        })
        if result.get("success"):
            return "Successfully typed search query"
        # Fallback selector
        result = _call_browser_service("type", {
            "selector": "input[name='search_query']",
            "text": "artificial intelligence",
            "timeout": 5000
        })
        if result.get("success"):
            return "Successfully typed search query"
        return f"Typing issue: {result.get('error', 'unknown')}"
    
    elif action == "click_search":
        # Press Enter is more reliable than clicking button
        result = _call_browser_service("press", {"key": "Enter"})
        if result.get("success"):
            time.sleep(3)  # Wait for results to load
            return "Successfully executed the search"
        # Fallback: try clicking the button
        result = _call_browser_service("click", {"selector": "button#search-icon-legacy", "timeout": 5000})
        if result.get("success"):
            time.sleep(3)
            return "Successfully clicked search button"
        return f"Search issue: {result.get('error', 'unknown')}"
    
    elif action == "click_video":
        # Wait for results, then click first video
        time.sleep(2)  # Extra wait for YouTube to render results
        
        # Strategy 1: Standard video renderer
        selectors = [
            "ytd-video-renderer:first-of-type a#video-title",
            "ytd-video-renderer a#video-title",
            "a#video-title",
            "ytd-rich-item-renderer a#video-title-link",
        ]
        
        for selector in selectors:
            result = _call_browser_service("click", {"selector": selector, "timeout": 8000})
            if result.get("success"):
                # VERIFICATION: Wait for URL to change to watch page
                time.sleep(2)
                for _ in range(5):  # Poll for 5 seconds
                    video_state = _get_video_state()
                    if "watch?v=" in video_state.get("url", ""):
                        # Video page loaded, now wait for video element
                        if video_state.get("exists") and video_state.get("readyState", 0) > 0:
                            return "Successfully selected and loaded video"
                    time.sleep(1)
                # URL changed but video not ready yet
                if "watch?v=" in video_state.get("url", ""):
                    return "Video page opened (loading...)"
        
        # If on retry, try scrolling down first
        if retry_attempt > 0:
            _call_browser_service("scroll", {"direction": "down", "amount": 300})
            time.sleep(1)
            result = _call_browser_service("click", {"selector": "ytd-video-renderer a#video-title", "timeout": 5000})
            if result.get("success"):
                time.sleep(3)
                return "Successfully selected a video"
        
        return f"Video selection issue: Could not find clickable video"
    
    elif action == "pause_video":
        # VERIFIED pause: Use YouTube's "K" keyboard shortcut (more reliable than clicking)
        video_state = _get_video_state()
        
        if not video_state.get("exists"):
            time.sleep(2)  # Wait for video element
            video_state = _get_video_state()
        
        if not video_state.get("exists"):
            return "Video element not found - page may still be loading"
        
        was_paused = video_state.get("paused", False)
        
        # Use "K" shortcut to toggle play/pause (works even with overlays)
        _call_browser_service("press", {"key": "k"})
        time.sleep(0.5)
        
        # Verify state changed
        new_state = _get_video_state()
        if new_state.get("paused", False) and not was_paused:
            return "Successfully paused the video"
        elif not new_state.get("paused", True) and was_paused:
            return "Successfully resumed the video"
        
        # Try one more time
        _call_browser_service("press", {"key": "k"})
        time.sleep(0.5)
        final_state = _get_video_state()
        if final_state.get("paused", False):
            return "Successfully paused the video"
        
        return "Pause command sent - video state may take a moment to update"
    
    return "Unknown action"


def _generate_demo_response(step_info: dict, step_number: int, action_result: str, user_context: dict, is_retry: bool = False) -> str:
    """Generate chat response - detailed for display, separate from voice."""
    
    user_name = user_context.get('name', 'there') if user_context else 'there'
    
    # Special case for intro step
    if step_number == 0:
        return f"""🎬 **Welcome to the YouTube Demo!**

Hi {user_name}! I'm Ravi, and I'll be your guide today.

I'm going to show you how our AI agent can interact with YouTube by:
1. **Searching** for "artificial intelligence" videos
2. **Selecting** a video from the results
3. **Controlling** playback

Ready to start? Just say **"yes"** or **"start"** when you're ready!"""
    
    # Special case for completion step
    if step_number == 6:
        return f"""✅ **Demo Complete!**

Great job following along, {user_name}! You've just seen our AI agent:
- Navigate to YouTube
- Search for content
- Select and control video playback

**Interested in having this capability for YOUR product?**

📞 Book a demo with our sales team: **+1-555-0199**
📧 Or email us at: **sales@keeto.ai**

Is there anything else you'd like to know about Keeto?"""
    
    # Retry message
    if is_retry:
        return f"I'm having a bit of trouble with this step. Let me try again... Say **'yes'** to retry or **'skip'** to move on."
    
    # Use LLM for other steps
    context_str = f"Name: {user_name}"
    if user_context:
        if user_context.get("role"):
            context_str += f", Role: {user_context['role']}"
        if user_context.get("company"):
            context_str += f", Company: {user_context['company']}"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", DEMO_AGENT_PROMPT.format(
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
        return f"Done with step {step_number}. Say 'next' to continue."


def demo_node(state: AgentState) -> dict:
    """
    Handles the guided demo workflow.
    - Split Brain: Returns both chat text and voice_script
    - Smart Retry: Tracks failures and retries before skipping
    """
    messages = state.get("messages", [])
    demo = state.get("demo") or {}
    user_context = state.get("user_context", {})
    
    user_name = user_context.get("name", "there") if user_context else "there"
    
    # Initialize demo if not active
    if not demo.get("is_active"):
        print("🎬 Initializing demo workflow")
        step_info = DEMO_STEPS[0]
        response = _generate_demo_response(step_info, 0, "", user_context)
        voice_script = step_info.get("voice_script", "")
        return {
            "messages": [AIMessage(content=response, additional_kwargs={"voice_text": voice_script})],
            "demo": {
                "is_active": True,
                "step": 0,
                "target_site": "youtube",
                "awaiting_confirmation": True,
                "retry_count": 0,
            }
        }
    
    current_step = demo.get("step", 0)
    awaiting = demo.get("awaiting_confirmation", False)
    retry_count = demo.get("retry_count", 0)
    
    # Check user input
    if awaiting and messages:
        last_message = messages[-1]
        if isinstance(last_message, HumanMessage):
            user_text = last_message.content.lower()
            confirmations = ["yes", "yeah", "yep", "ok", "okay", "sure", "start", "go", "continue", "next"]
            
            if any(conf in user_text for conf in confirmations):
                current_step += 1
                awaiting = False
                retry_count = 0  # Reset on user confirmation
            elif "skip" in user_text:
                current_step += 1
                awaiting = False
                retry_count = 0
                print(f"🎬 User skipped step {current_step - 1}")
            elif any(word in user_text for word in ["no", "stop", "cancel", "exit", "quit"]):
                return {
                    "messages": [AIMessage(content=f"No problem, {user_name}! Demo cancelled.", additional_kwargs={"voice_text": "Demo cancelled. Talk to you later!"})],
                    "demo": {"is_active": False, "step": 0, "target_site": "", "awaiting_confirmation": False, "retry_count": 0}
                }
            else:
                # Check for interrupt commands (pause, play, etc.) BEFORE saying "I'm in demo mode"
                interrupt_result = _handle_interrupt_command(last_message.content, user_name)
                if interrupt_result:
                    return {
                        "messages": [AIMessage(content=interrupt_result["text"], additional_kwargs={"voice_text": interrupt_result["voice"]})],
                        "demo": demo  # Stay in current step
                    }
                
                return {
                    "messages": [AIMessage(content=f"I'm in demo mode, {user_name}. Say **'next'** to continue, **'pause'** to pause the video, or **'stop'** to exit.", additional_kwargs={"voice_text": "Say next to continue."})],
                    "demo": demo
                }
    
    # Get step info
    step_info = DEMO_STEPS.get(current_step, DEMO_STEPS[6])
    
    # Execute action if this step has one
    action_result = ""
    action_failed = False
    if step_info.get("action"):
        action_result = _execute_demo_action(step_info["action"], state, retry_attempt=retry_count)
        print(f"🎬 Demo action '{step_info['action']}': {action_result}")
        
        # Check if action failed
        if "issue" in action_result.lower() or "error" in action_result.lower():
            action_failed = True
    
    # Handle failed action with smart retry
    if action_failed:
        retry_count += 1
        if retry_count < 2:
            # Retry automatically
            print(f"🎬 Retrying step {current_step} (attempt {retry_count + 1})")
            response = _generate_demo_response(step_info, current_step, action_result, user_context, is_retry=True)
            voice_script = "Let me try that again."
            return {
                "messages": [AIMessage(content=response, additional_kwargs={"voice_text": voice_script})],
                "demo": {
                    "is_active": True,
                    "step": current_step,
                    "target_site": "youtube",
                    "awaiting_confirmation": True,  # Wait for user to say 'yes' to retry
                    "retry_count": retry_count,
                }
            }
        else:
            # After 2 retries, ask user
            response = f"I'm having trouble with this step after {retry_count} tries. Say **'skip'** to move on or **'yes'** to try once more."
            voice_script = "Having trouble. Say skip to move on."
            return {
                "messages": [AIMessage(content=response, additional_kwargs={"voice_text": voice_script})],
                "demo": {
                    "is_active": True,
                    "step": current_step,
                    "target_site": "youtube",
                    "awaiting_confirmation": True,
                    "retry_count": retry_count,
                }
            }
    
    # Generate response
    response = _generate_demo_response(step_info, current_step, action_result, user_context)
    voice_script = step_info.get("voice_script", "")
    
    # Update demo state
    new_demo = {
        "is_active": current_step < 6,
        "step": current_step if step_info.get("awaits_confirmation") else current_step + 1,
        "target_site": "youtube",
        "awaiting_confirmation": step_info.get("awaits_confirmation", False),
        "retry_count": 0,
    }
    
    if current_step >= 6:
        new_demo["is_active"] = False
    
    return {
        "messages": [AIMessage(content=response, additional_kwargs={"voice_text": voice_script})],
        "demo": new_demo
    }
