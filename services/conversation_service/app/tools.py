"""
Browser Tools for LangChain Agent.
Provides tools that allow the agent to control the browser service.
"""
import os
from typing import Optional

import httpx
from langchain.tools import Tool


BROWSER_SERVICE_URL = os.getenv("BROWSER_SERVICE_URL", "http://browser_service:8001")


async def _call_browser_api(endpoint: str, method: str = "POST", data: dict = None) -> dict:
    """Make an async HTTP call to the browser service."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{BROWSER_SERVICE_URL}{endpoint}"
        if method == "GET":
            response = await client.get(url)
        else:
            response = await client.post(url, json=data or {})
        response.raise_for_status()
        return response.json()


def _call_browser_api_sync(endpoint: str, method: str = "POST", data: dict = None) -> dict:
    """Make a sync HTTP call to the browser service."""
    with httpx.Client(timeout=30.0) as client:
        url = f"{BROWSER_SERVICE_URL}{endpoint}"
        if method == "GET":
            response = client.get(url)
        else:
            response = client.post(url, json=data or {})
        response.raise_for_status()
        return response.json()


def navigate_to_url(url: str) -> str:
    """
    Navigate the browser to a specific URL.
    
    Args:
        url: The full URL to navigate to (e.g., 'https://google.com')
    
    Returns:
        A message indicating success and the page title.
    """
    # Clean up the URL - LLM sometimes adds quotes
    url = url.strip().strip("'\"")
    
    # Ensure URL has a protocol
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    try:
        result = _call_browser_api_sync("/navigate", data={"url": url})
        if result.get("success"):
            data = result.get("data", {})
            return f"Successfully navigated to {url}. Page title: {data.get('title', 'Unknown')}"
        return f"Failed to navigate: {result.get('message', 'Unknown error')}"
    except Exception as e:
        return f"Error navigating to {url}: {str(e)}"


def click_element(selector: str) -> str:
    """
    Click an element on the current page.
    
    Args:
        selector: CSS selector for the element to click (e.g., 'button.submit', '#login-btn')
    
    Returns:
        A message indicating success or failure.
    """
    try:
        result = _call_browser_api_sync("/click", data={"selector": selector})
        if result.get("success"):
            return f"Successfully clicked element. [Give Final Answer NOW - say 'I clicked the button.']"
        return f"Failed to click: {result.get('message', 'Unknown error')}"
    except Exception as e:
        return f"Error clicking {selector}: {str(e)}"


def _smart_click(input_str: str) -> str:
    """
    Smart click function that handles various input formats.
    If input mentions 'search', tries common search button selectors.
    """
    input_str = input_str.strip().strip("'\"")
    
    # If it looks like a selector (has special chars), use directly
    if any(c in input_str for c in ['#', '.', '[', ']', '>', ' ']):
        return click_element(input_str)
    
    # Check if user wants to click search
    if 'search' in input_str.lower():
        search_selectors = [
            'button#search-icon-legacy',  # YouTube search button
            'button[aria-label="Search"]',  # YouTube
            'input[type="submit"]',  # Google
            'button[type="submit"]',  # Generic
            'button[aria-label="Google Search"]',  # Google
        ]
        for selector in search_selectors:
            try:
                result = click_element(selector)
                if "Successfully" in result:
                    return result
            except Exception:
                continue
        return "Could not find search button. The search may have already been submitted."
    
    # Try the input as a selector anyway
    return click_element(input_str)


def type_into_field(selector: str, text: str) -> str:
    """
    Type text into an input field on the current page.
    
    Args:
        selector: CSS selector for the input field (e.g., 'input[name="search"]', '#email')
        text: The text to type into the field
    
    Returns:
        A message indicating success or failure.
    """
    try:
        result = _call_browser_api_sync("/type", data={"selector": selector, "text": text})
        if result.get("success"):
            return f"Successfully typed '{text}' into the search field. [Give Final Answer NOW - say 'I typed {text} in the search field.']"
        return f"Failed to type: {result.get('message', 'Unknown error')}"
    except Exception as e:
        return f"Error typing into {selector}: {str(e)}"


def get_page_text(selector: Optional[str] = None) -> str:
    """
    Get the text content from the current page or a specific element.
    
    Args:
        selector: Optional CSS selector. If not provided, returns all page text.
    
    Returns:
        The text content of the page or element.
    """
    try:
        data = {"selector": selector} if selector else {}
        result = _call_browser_api_sync("/get-text", data=data)
        if result.get("success"):
            text = result.get("data", {}).get("text", "")
            # Truncate if too long for the LLM context
            if len(text) > 1000:
                text = text[:1000] + "..."
            # Add stop instruction to prevent agent from looping
            return f"{text}\n\n[IMPORTANT: You have the page content. Give Final Answer NOW. Do NOT call more tools.]"
        return f"Failed to get text: {result.get('message', 'Unknown error')}"
    except Exception as e:
        return f"Error getting text: {str(e)}"


def get_current_page_info() -> str:
    """
    Get information about the current page (URL and title).
    
    Returns:
        Current page URL and title.
    """
    try:
        result = _call_browser_api_sync("/page-info", method="GET")
        if result.get("success"):
            data = result.get("data", {})
            return f"Current page: {data.get('title', 'Unknown')} ({data.get('url', 'Unknown')})"
        return f"Failed to get page info: {result.get('message', 'Unknown error')}"
    except Exception as e:
        return f"Error getting page info: {str(e)}"


def _smart_type(input_str: str) -> str:
    """
    Smart type function that handles various input formats.
    If no selector provided, tries common search input selectors.
    """
    input_str = input_str.strip().strip("'\"")
    
    # If format is "selector|text", use as-is
    if "|" in input_str:
        parts = input_str.split("|", 1)
        return type_into_field(parts[0].strip(), parts[1].strip())
    
    # Otherwise, try common search selectors
    text = input_str
    common_selectors = [
        'input[name="search_query"]',  # YouTube
        'textarea[name="q"]',           # Google
        'input[name="q"]',              # Google fallback
        'input[type="search"]',         # Generic
        'input[placeholder*="earch"]',  # Generic with "Search" placeholder
    ]
    
    for selector in common_selectors:
        try:
            result = type_into_field(selector, text)
            if "Successfully" in result:
                return result
        except Exception:
            continue
    
    return f"Could not find a search input field. Try specifying the selector: 'selector|{text}'"

# --- LangChain Tool Definitions ---

browser_tools = [
    Tool(
        name="navigate_browser",
        func=navigate_to_url,
        description="Navigate the browser to a specific URL. Use this when you need to go to a website. Input should be a full URL like 'https://google.com'."
    ),
    Tool(
        name="click_element",
        func=_smart_click,
        description="Click a button or element. For search buttons, just say 'search'. For other elements, provide a CSS selector."
    ),
    Tool(
        name="type_text",
        func=lambda x: _smart_type(x),
        description="Type text into a search or input field. Input format: 'text to type' OR 'selector|text'. Examples: 'hello world' or 'input[name=search]|hello'."
    ),
    Tool(
        name="get_page_text",
        func=get_page_text,
        description="Get the text content from the current page. Optionally provide a CSS selector to get text from a specific element."
    ),
    Tool(
        name="get_page_info",
        func=lambda _: get_current_page_info(),
        description="Get the current page URL and title. Use this to check where the browser currently is."
    ),
]
