"""
Main Graph Builder.
Assembles all nodes and edges into the final LangGraph StateGraph.
"""
import os
import uuid
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.postgres import PostgresSaver

from .state import AgentState
from .nodes import router_node, chat_node, route_by_intent
from .tool_nodes import navigate_node, enrich_node, crm_node


def create_sales_agent_graph(checkpointer=None):
    """
    Creates and compiles the Sales Agent graph.
    
    Args:
        checkpointer: Optional PostgresSaver for persistence.
    
    Returns:
        Compiled StateGraph.
    """
    # Initialize the graph with our state schema
    graph = StateGraph(AgentState)
    
    # --- Add Nodes ---
    graph.add_node("router", router_node)
    graph.add_node("chat", chat_node)
    graph.add_node("navigate", navigate_node)
    graph.add_node("enrich", enrich_node)
    graph.add_node("crm", crm_node)
    
    # --- Add Edges ---
    # Start -> Router (always route first)
    graph.add_edge(START, "router")
    
    # Router -> Conditional routing based on intent
    graph.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "chat": "chat",
            "navigate": "navigate",
            "enrich": "enrich",
            "crm": "crm",
        }
    )
    
    # All action nodes -> END (single turn for now)
    graph.add_edge("chat", END)
    graph.add_edge("navigate", END)
    graph.add_edge("enrich", END)
    graph.add_edge("crm", END)
    
    # Compile with optional checkpointer
    if checkpointer:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()


def get_postgres_checkpointer():
    """
    Creates a PostgresSaver for conversation persistence.
    Uses the existing postgres container.
    
    The PostgresSaver requires:
    - autocommit=True (required for setup() to create indexes)
    - row_factory=dict_row (required for checkpoint operations)
    """
    from psycopg_pool import ConnectionPool
    from psycopg.rows import dict_row
    from psycopg import Connection
    
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://agent_user:agent_password@postgres:5432/agent_db"
    )
    
    try:
        # First, run setup with a single connection (required for CREATE INDEX CONCURRENTLY)
        print("📦 Setting up checkpoint tables...")
        with Connection.connect(
            db_url, autocommit=True, prepare_threshold=0, row_factory=dict_row
        ) as conn:
            temp_checkpointer = PostgresSaver(conn)
            temp_checkpointer.setup()
        print("✅ Checkpoint tables created/verified")
        
        # Now create a connection pool for runtime use
        # Configure pool to use autocommit and dict_row
        pool = ConnectionPool(
            conninfo=db_url,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
            min_size=1,
            max_size=5,
        )
        
        checkpointer = PostgresSaver(pool)
        print("✅ Postgres checkpointer initialized with connection pool")
        return checkpointer
        
    except Exception as e:
        print(f"⚠️ Failed to initialize Postgres checkpointer: {e}")
        import traceback
        traceback.print_exc()
        print("  Falling back to memory-only mode")
        return None


# --- Module-level graph instance ---
# This will be initialized on first import
_graph = None
_checkpointer = None


def get_graph():
    """
    Returns the singleton graph instance.
    Initializes on first call.
    """
    global _graph, _checkpointer
    
    if _graph is None:
        _checkpointer = get_postgres_checkpointer()
        _graph = create_sales_agent_graph(checkpointer=_checkpointer)
        print("🧠 LangGraph Sales Agent initialized")
    
    return _graph


def invoke_graph(user_input: str, session_id: str = None) -> str:
    """
    Convenience function to invoke the graph with a user message.
    
    Args:
        user_input: The user's message.
        session_id: Optional session ID for persistence.
    
    Returns:
        The agent's response as a string.
    """
    from langchain_core.messages import HumanMessage
    
    graph = get_graph()
    
    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Build initial state
    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "user_context": None,
        "session_id": session_id,
        "current_url": None,
        "lead_score": 0,
        "next_action": None,
    }
    
    # Config for checkpointer
    config = {"configurable": {"thread_id": session_id}}
    
    try:
        # Invoke the graph
        result = graph.invoke(initial_state, config=config)
        
        # Extract response from messages
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            if hasattr(last_message, 'content'):
                return last_message.content
            return str(last_message)
        
        return "I processed your request but have no response."
    
    except Exception as e:
        print(f"Graph invocation error: {e}")
        return f"Error: {e}"
