"""
Tool Nodes for LangGraph.
These nodes wrap existing tools from the original agent.
"""
import re
from langchain_core.messages import AIMessage

from .state import AgentState

# Import the actual tool functions directly
from ..tools import navigate_to_url, get_current_page_info, _smart_type, _smart_click
from ..enrichment_tools import enrichment_tools
from ..crm_tools import crm_tools


# --- Navigator Node ---

def navigate_node(state: AgentState) -> dict:
    """
    Handles browser navigation tasks.
    Extracts URL/action from user message and calls the appropriate tool.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"messages": [AIMessage(content="No message to process.")]}
    
    last_message = messages[-1]
    content = last_message.content if hasattr(last_message, 'content') else str(last_message)
    content_lower = content.lower()
    
    try:
        # Detect navigation intent
        if "go to" in content_lower or "navigate to" in content_lower or "open" in content_lower:
            # Extract URL from message
            url_match = re.search(r'(?:go to|navigate to|open)\s+(\S+)', content_lower)
            if url_match:
                url = url_match.group(1).strip()
                # Call the actual navigate_to_url function
                result = navigate_to_url(url)
                return {
                    "messages": [AIMessage(content=result)],
                    "current_url": url if "Successfully" in result else state.get("current_url")
                }
        
        # Detect typing intent
        elif "type" in content_lower or "search for" in content_lower or "enter" in content_lower:
            # Extract what to type
            text_match = re.search(r'(?:type|search for|enter)\s+["\']?(.+?)["\']?$', content_lower)
            if text_match:
                text = text_match.group(1).strip().strip('"\'')
                result = _smart_type(text)
                return {"messages": [AIMessage(content=result)]}
        
        # Detect click intent
        elif "click" in content_lower:
            target_match = re.search(r'click\s+(?:on\s+)?(?:the\s+)?(.+)', content_lower)
            if target_match:
                target = target_match.group(1).strip()
                result = _smart_click(target)
                return {"messages": [AIMessage(content=result)]}
        
        # Detect page info request
        elif "what page" in content_lower or "where am i" in content_lower or "current page" in content_lower:
            result = get_current_page_info()
            return {"messages": [AIMessage(content=result)]}
        
        # Default: try to interpret as navigation
        # Look for a URL-like pattern anywhere in the message
        url_pattern = re.search(r'(\w+\.\w+(?:\.\w+)?(?:/\S*)?)', content)
        if url_pattern:
            url = url_pattern.group(1)
            result = navigate_to_url(url)
            return {
                "messages": [AIMessage(content=result)],
                "current_url": url if "Successfully" in result else state.get("current_url")
            }
        
        return {"messages": [AIMessage(content="I'm not sure what browser action you want. Try: 'go to google.com', 'type hello', or 'click search'.")]}
    
    except Exception as e:
        return {"messages": [AIMessage(content=f"Navigation error: {e}")]}


# --- Enrichment Node ---
def enrich_node(state: AgentState) -> dict:
    """
    Handles company/person research.
    Uses the existing enrichment_tools.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"messages": [AIMessage(content="No message to process.")]}
    
    last_message = messages[-1]
    query = last_message.content if hasattr(last_message, 'content') else str(last_message)
    
    # Extract the search subject from the message
    # Simple extraction - in production, use LLM to parse
    search_query = query.replace("find info about", "").replace("look up", "").replace("research", "").strip()
    
    try:
        # Use the lookup_company tool
        lookup_tool = next((t for t in enrichment_tools if t.name == "lookup_company"), None)
        if lookup_tool:
            result = lookup_tool.func(search_query)
            return {"messages": [AIMessage(content=result)]}
        return {"messages": [AIMessage(content="Enrichment tool not available.")]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"Enrichment error: {e}")]}


# --- CRM Node ---
def crm_node(state: AgentState) -> dict:
    """
    Handles lead management (save, list).
    Uses the existing crm_tools.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"messages": [AIMessage(content="No message to process.")]}
    
    last_message = messages[-1]
    content = last_message.content if hasattr(last_message, 'content') else str(last_message)
    content_lower = content.lower()
    
    try:
        # Determine which CRM action
        if "save" in content_lower or "add" in content_lower:
            save_tool = next((t for t in crm_tools if t.name == "save_lead"), None)
            if save_tool:
                # Extract lead info from message
                lead_info = content.replace("save lead:", "").replace("save this lead:", "").strip()
                result = save_tool.func(lead_info)
                return {"messages": [AIMessage(content=result)]}
        
        elif "list" in content_lower or "show" in content_lower:
            list_tool = next((t for t in crm_tools if t.name == "list_leads"), None)
            if list_tool:
                result = list_tool.func("")
                return {"messages": [AIMessage(content=result)]}
        
        return {"messages": [AIMessage(content="I can save leads or list leads. What would you like to do?")]}
    
    except Exception as e:
        return {"messages": [AIMessage(content=f"CRM error: {e}")]}
