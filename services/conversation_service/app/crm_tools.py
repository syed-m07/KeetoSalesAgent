"""
CRM Tools for LangChain Agent.
Provides tools for saving and managing leads via the CRM service.
"""
import os
import httpx
from langchain.tools import Tool


CRM_SERVICE_URL = os.getenv("CRM_SERVICE_URL", "http://crm_service:8003")


def _call_crm_api_sync(
    endpoint: str, method: str = "POST", data: dict = None
) -> dict:
    """Make a sync HTTP call to the CRM service."""
    with httpx.Client(timeout=30.0) as client:
        url = f"{CRM_SERVICE_URL}{endpoint}"
        if method == "GET":
            response = client.get(url)
        elif method == "POST":
            response = client.post(url, json=data or {})
        else:
            response = client.request(method, url, json=data or {})
        response.raise_for_status()
        return response.json()


def save_lead(input_str: str) -> str:
    """
    Save a lead to the CRM.

    Args:
        input_str: Lead information in format "name|email|company|summary"
                   or just "name" for minimal lead.

    Returns:
        Confirmation message with lead ID.
    """
    input_str = input_str.strip().strip("'\"")

    # Parse input - support multiple formats
    parts = [p.strip() for p in input_str.split("|")]

    lead_data = {"name": parts[0] if parts else "Unknown"}

    if len(parts) > 1:
        lead_data["email"] = parts[1]
    if len(parts) > 2:
        lead_data["company"] = parts[2]
    if len(parts) > 3:
        lead_data["summary"] = parts[3]

    try:
        result = _call_crm_api_sync("/leads", method="POST", data=lead_data)
        lead_id = result.get("id", "unknown")
        name = result.get("name", "Unknown")
        return f"✅ Lead '{name}' saved successfully! ID: {lead_id}"

    except Exception as e:
        return f"❌ Error saving lead: {str(e)}"


def list_leads(input_str: str = "") -> str:
    """
    List all leads from the CRM.

    Args:
        input_str: Optional status filter (e.g., "new", "qualified").

    Returns:
        Formatted list of leads.
    """
    try:
        endpoint = "/leads"
        if input_str and input_str.strip():
            endpoint = f"/leads?status={input_str.strip()}"

        results = _call_crm_api_sync(endpoint, method="GET")

        if not results:
            return "📋 No leads found in the CRM."

        response = f"📋 **Leads ({len(results)} total):**\n"
        for lead in results[:10]:  # Limit to 10 for readability
            name = lead.get("name", "Unknown")
            email = lead.get("email", "N/A")
            status = lead.get("status", "new")
            company = lead.get("company", "")
            company_info = f" @ {company}" if company else ""
            response += f"- {name}{company_info} ({email}) - {status}\n"

        if len(results) > 10:
            response += f"\n... and {len(results) - 10} more leads."

        return response

    except Exception as e:
        return f"❌ Error listing leads: {str(e)}"


# --- LangChain Tool Definitions ---

crm_tools = [
    Tool(
        name="save_lead",
        func=save_lead,
        description=(
            "Save a new lead to the CRM database. "
            "Input format: 'name|email|company|summary' or just 'name' for minimal lead. "
            "Example: 'John Doe|john@example.com|Acme Corp|Interested in enterprise plan'"
        ),
    ),
    Tool(
        name="list_leads",
        func=list_leads,
        description=(
            "List all leads from the CRM. "
            "Optionally filter by status: 'new', 'contacted', 'qualified', 'converted', 'lost'."
        ),
    ),
]
