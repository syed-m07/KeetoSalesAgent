"""
Enrichment Service - Company Information Lookup
Uses Google Search to find information about companies/prospects.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from .search import search_company_info

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Enrichment Service",
    description="Company information enrichment via Google Search",
    version="1.0.0",
)

# Prometheus metrics
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)


class EnrichRequest(BaseModel):
    """Request model for enrichment."""

    query: str
    num_results: Optional[int] = 5


class EnrichResponse(BaseModel):
    """Response model for enrichment."""

    query: str
    results: list[dict]
    summary: str


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "enrichment"}


@app.post("/enrich", response_model=EnrichResponse)
async def enrich_company(request: EnrichRequest):
    """
    Enrich company information using Google Search.

    Args:
        request: Contains the query (company name) and optional num_results.

    Returns:
        EnrichResponse with search results and a summary.
    """
    try:
        logger.info(f"Enrichment request for: {request.query}")
        results = search_company_info(request.query, request.num_results)

        # Create a simple summary from results
        if results:
            summary = f"Found {len(results)} results for '{request.query}'. "
            summary += f"Top result: {results[0].get('title', 'N/A')}"
        else:
            summary = f"No results found for '{request.query}'."

        return EnrichResponse(query=request.query, results=results, summary=summary)

    except Exception as e:
        logger.error(f"Enrichment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "Enrichment Service",
        "version": "1.0.0",
        "endpoints": {
            "/health": "Health check",
            "/enrich": "POST - Enrich company information",
        },
    }
