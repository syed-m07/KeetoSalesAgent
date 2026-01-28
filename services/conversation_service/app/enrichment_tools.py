"""
Enrichment Tools for LangChain Agent.
Provides tools for looking up company information via the enrichment service.
"""
import os
import httpx
from langchain.tools import Tool


ENRICHMENT_SERVICE_URL = os.getenv(
    "ENRICHMENT_SERVICE_URL", "http://enrichment_service:8002"
)


def _call_enrichment_api_sync(endpoint: str, data: dict = None) -> dict:
    """Make a sync HTTP call to the enrichment service."""
    with httpx.Client(timeout=30.0) as client:
        url = f"{ENRICHMENT_SERVICE_URL}{endpoint}"
        response = client.post(url, json=data or {})
        response.raise_for_status()
        return response.json()


def enrich_company(query: str) -> str:
    """
    Look up information about a company or prospect using Google Search.

    Args:
        query: The company name or search query.

    Returns:
        A summary of search results about the company.
    """
    query = query.strip().strip("'\"")

    try:
        result = _call_enrichment_api_sync("/enrich", data={"query": query})
        summary = result.get("summary", "No results found.")
        results = result.get("results", [])

        # Build a readable response
        response = f"**Enrichment Results for '{query}':**\n{summary}\n\n"

        if results:
            response += "**Top Results:**\n"
            for i, r in enumerate(results[:3], 1):
                title = r.get("title", "Unknown")
                url = r.get("url", "")
                response += f"{i}. {title}\n   {url}\n"

        return response

    except Exception as e:
        return f"Error looking up '{query}': {str(e)}"


# --- LangChain Tool Definitions ---

enrichment_tools = [
    Tool(
        name="lookup_company",
        func=enrich_company,
        description=(
            "Look up information about a company or prospect using Google Search. "
            "Input should be a company name like 'OpenAI' or 'Microsoft'. "
            "Use this when the user asks for information about a company."
        ),
    ),
]
