"""
Google Search module for company enrichment.
Uses googlesearch-python for free searches (rate-limited).
Falls back to mock data when rate-limited.
"""

import logging
from typing import Optional

try:
    from googlesearch import search
except ImportError:
    search = None

logger = logging.getLogger(__name__)


# Mock data for common companies (fallback when rate-limited)
MOCK_COMPANY_DATA = {
    "openai": [
        {
            "title": "OpenAI - Official Website",
            "url": "https://openai.com",
            "description": "OpenAI is an AI research company. Creators of ChatGPT, GPT-4, DALL-E.",
        },
        {
            "title": "OpenAI - Wikipedia",
            "url": "https://en.wikipedia.org/wiki/OpenAI",
            "description": "Founded in 2015, OpenAI is an AI research lab based in San Francisco.",
        },
    ],
    "microsoft": [
        {
            "title": "Microsoft Corporation",
            "url": "https://microsoft.com",
            "description": "Microsoft is a technology company known for Windows, Office, and Azure.",
        },
    ],
    "google": [
        {
            "title": "Google - About",
            "url": "https://about.google",
            "description": "Google is a technology company specializing in search, cloud, and AI.",
        },
    ],
}


def search_company_info(query: str, num_results: Optional[int] = 5) -> list[dict]:
    """
    Search Google for company information.
    Falls back to mock data if rate-limited.

    Args:
        query: The company name or search query.
        num_results: Number of results to return (default 5).

    Returns:
        List of dictionaries containing search results.
    """
    results = []
    query_lower = query.lower().strip()

    # Try Google search first
    if search is not None:
        try:
            search_query = f"{query} company info"
            for url in search(search_query, num_results=num_results, lang="en"):
                results.append(
                    {
                        "title": extract_title_from_url(url),
                        "url": url,
                        "description": f"Search result from {extract_domain(url)}",
                    }
                )
            if results:
                logger.info(f"Found {len(results)} Google results for '{query}'")
                return results
        except Exception as e:
            logger.warning(f"Google search failed: {e}")

    # Fallback: Check mock data
    for key, mock_results in MOCK_COMPANY_DATA.items():
        if key in query_lower:
            logger.info(f"Using mock data for '{query}'")
            return mock_results

    # Final fallback: Generic response
    logger.info(f"No results found, returning generic response for '{query}'")
    return [
        {
            "title": f"Search results for {query}",
            "url": f"https://www.google.com/search?q={query.replace(' ', '+')}",
            "description": f"Google search rate-limited. Visit the link to search manually for {query}.",
        }
    ]


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse

        return urlparse(url).netloc
    except Exception:
        return url


def extract_title_from_url(url: str) -> str:
    """Extract a readable title from URL path."""
    try:
        from urllib.parse import urlparse, unquote

        parsed = urlparse(url)
        path = unquote(parsed.path)
        segments = [s for s in path.split("/") if s]
        if segments:
            title = segments[-1].replace("-", " ").replace("_", " ").title()
            return f"{title} - {parsed.netloc}"
        return parsed.netloc
    except Exception:
        return url

