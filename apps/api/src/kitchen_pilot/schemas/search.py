"""Request/response schemas for web search endpoints."""

from pydantic import BaseModel, Field


class RecipeSearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source: str  # domain name, e.g. "allrecipes.com"
    score: float = 0.0


class RecipeSearchResponse(BaseModel):
    results: list[RecipeSearchResult] = Field(default_factory=list)
    query: str
    provider: str  # "tavily" or "brave"


class ExtractRequest(BaseModel):
    url: str = Field(min_length=1, description="URL to extract recipe content from")


class ExtractResponse(BaseModel):
    url: str
    content: str
