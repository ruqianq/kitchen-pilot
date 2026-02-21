"""Web search router — recipe discovery endpoints."""

from fastapi import APIRouter, HTTPException, Query

from kitchen_pilot.schemas.search import (
    ExtractRequest,
    ExtractResponse,
    RecipeSearchResponse,
)
from kitchen_pilot.services import web_search
from kitchen_pilot.services.web_search import WebSearchError

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/recipes", response_model=RecipeSearchResponse)
async def search_recipes(
    q: str = Query(..., min_length=1, max_length=200),
    max_results: int = Query(5, ge=1, le=10),
):
    """Search the web for recipes."""
    try:
        results, provider = await web_search.search_recipes(q, max_results)
    except WebSearchError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return RecipeSearchResponse(results=results, query=q, provider=provider)


@router.post("/recipes/extract", response_model=ExtractResponse)
async def extract_recipe(request: ExtractRequest):
    """Extract full recipe content from a URL (Tavily only)."""
    try:
        content = await web_search.extract_recipe(request.url)
    except WebSearchError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    if content is None:
        raise HTTPException(
            status_code=400,
            detail="Content extraction requires Tavily. Set TAVILY_API_KEY.",
        )

    return ExtractResponse(url=request.url, content=content)
