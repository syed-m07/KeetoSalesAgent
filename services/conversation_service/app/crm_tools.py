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
                   or "name, email, company, summary" (comma-separated)
                   or just "name" for minimal lead.

    Returns:
        Confirmation message with lead ID.
    """
    import re

    input_str = input_str.strip().strip("'\"")

    # Strip common prefixes the LLM might include
    prefixes_to_strip = [
        "save a lead:", "save lead:", "add a lead:", "add lead:",
        "create a lead:", "create lead:", "new lead:",
    ]
    lower = input_str.lower()
    for prefix in prefixes_to_strip:
        if lower.startswith(prefix):
            input_str = input_str[len(prefix):].strip()
            break

    # Detect delimiter: pipe or comma
    if "|" in input_str:
        parts = [p.strip() for p in input_str.split("|")]
    else:
        parts = [p.strip() for p in input_str.split(",")]

    # Smart field detection: find email by pattern, rest by position
    email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

    lead_data = {"name": parts[0] if parts else "Unknown"}

    if len(parts) > 1:
        # Look through remaining parts for email, company, summary
        remaining = parts[1:]
        for part in remaining:
            part = part.strip()
            if email_pattern.match(part) and "email" not in lead_data:
                lead_data["email"] = part
            elif "email" not in lead_data and "@" in part:
                lead_data["email"] = part
            elif "company" not in lead_data and not email_pattern.match(part):
                lead_data["company"] = part
            elif "summary" not in lead_data:
                lead_data["summary"] = part

    # If we have 4+ parts in original order: name, email, company, summary
    if len(parts) >= 4 and "email" not in lead_data:
        lead_data["email"] = parts[1]
        lead_data["company"] = parts[2]
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
