"""Web search service for recipe discovery.

Supports Tavily (primary) and Brave Search (fallback).
Uses httpx for direct HTTP calls — no extra Python libraries needed.
"""

import logging
from urllib.parse import urlparse

import httpx

from kitchen_pilot.config import settings
from kitchen_pilot.schemas.search import RecipeSearchResult

logger = logging.getLogger(__name__)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"
TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


class WebSearchError(Exception):
    """Raised when a web search operation fails."""


def get_provider() -> str:
    """Return the configured search provider name."""
    if settings.tavily_api_key:
        return "tavily"
    if settings.brave_api_key:
        return "brave"
    raise WebSearchError(
        "No search API key configured. Set TAVILY_API_KEY or BRAVE_API_KEY."
    )


def _extract_domain(url: str) -> str:
    """Extract domain name from a URL."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        return host.removeprefix("www.")
    except Exception:
        return ""


# ── Tavily ───────────────────────────────────────────────


async def _search_tavily(
    query: str,
    max_results: int = 5,
) -> list[RecipeSearchResult]:
    """Search via Tavily API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            TAVILY_SEARCH_URL,
            json={
                "api_key": settings.tavily_api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
                "include_answer": False,
            },
        )

    if response.status_code != 200:
        logger.error("Tavily search error: %s", response.text)
        raise WebSearchError(f"Tavily search failed: {response.status_code}")

    data = response.json()
    results = []
    for i, item in enumerate(data.get("results", [])):
        results.append(
            RecipeSearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", "")[:500],
                source=_extract_domain(item.get("url", "")),
                score=item.get("score", 1.0 - i * 0.1),
            )
        )
    return results


async def extract_recipe(url: str) -> str | None:
    """Extract full content from a URL using Tavily Extract API.

    Returns None if Tavily is not configured.
    """
    if not settings.tavily_api_key:
        return None

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            TAVILY_EXTRACT_URL,
            json={
                "api_key": settings.tavily_api_key,
                "urls": [url],
            },
        )

    if response.status_code != 200:
        logger.error("Tavily extract error: %s", response.text)
        raise WebSearchError(f"Content extraction failed: {response.status_code}")

    data = response.json()
    results = data.get("results", [])
    if results:
        return results[0].get("raw_content", "") or results[0].get("content", "")
    return None


# ── Brave ────────────────────────────────────────────────


async def _search_brave(
    query: str,
    max_results: int = 5,
) -> list[RecipeSearchResult]:
    """Search via Brave Search API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            BRAVE_SEARCH_URL,
            headers={
                "X-Subscription-Token": settings.brave_api_key,
                "Accept": "application/json",
            },
            params={"q": query, "count": max_results},
        )

    if response.status_code != 200:
        logger.error("Brave search error: %s", response.text)
        raise WebSearchError(f"Brave search failed: {response.status_code}")

    data = response.json()
    results = []
    for i, item in enumerate(data.get("web", {}).get("results", [])):
        results.append(
            RecipeSearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("description", "")[:500],
                source=_extract_domain(item.get("url", "")),
                score=1.0 - i * 0.1,
            )
        )
    return results


# ── Public API ───────────────────────────────────────────


async def search_recipes(
    query: str,
    max_results: int = 5,
) -> tuple[list[RecipeSearchResult], str]:
    """Search for recipes on the web.

    Returns (results, provider_name).
    Automatically appends "recipe" to query if not present.
    """
    provider = get_provider()

    # Ensure "recipe" is in the query for better results
    q = query.strip()
    if "recipe" not in q.lower():
        q = f"{q} recipe"

    if provider == "tavily":
        results = await _search_tavily(q, max_results)
    else:
        results = await _search_brave(q, max_results)

    return results, provider
