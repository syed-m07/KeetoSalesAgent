"""
Agent State Definition for LangGraph.
This is the shared state object that flows through all nodes in the graph.
"""
from typing import Annotated, TypedDict, Optional, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from .demo_state import DemoState


class UserContext(TypedDict, total=False):
    """User context loaded from database."""
    user_id: str
    name: str
    email: str
    company: str
    role: str  # e.g., "CTO", "Developer", "Sales Manager"


class AgentState(TypedDict):
    """
    The central state object for the Sales Agent graph.
    
    Attributes:
        messages: The conversation history (managed by add_messages reducer).
        user_context: Information about the logged-in user.
        current_url: The current browser page URL.
        lead_score: Qualification score (0-100) for the current lead.
        next_action: Hint for what the agent should do next.
        session_id: Unique identifier for this conversation session.
        demo: State for guided demo workflow.
    """
    # Core conversation state - uses LangGraph's message reducer
    messages: Annotated[List[BaseMessage], add_messages]
    
    # User identity and context
    user_context: Optional[UserContext]
    session_id: str
    
    # Browser state
    current_url: Optional[str]
    
    # Sales intelligence
    lead_score: int  # 0-100, updated by enrichment/analysis
    
    # Routing hints
    next_action: Optional[str]  # "navigate", "enrich", "crm", "chat", "demo"
    
    # Demo workflow state
    demo: Optional[DemoState]
