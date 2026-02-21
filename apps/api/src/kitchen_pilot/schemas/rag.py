"""Schemas for RAG ingestion and search endpoints."""

from pydantic import BaseModel, Field


class DriveIngestRequest(BaseModel):
    folder_id: str | None = Field(
        default=None,
        description="Optional Google Drive folder ID to limit ingestion scope",
    )


class DriveIngestResponse(BaseModel):
    files_processed: int
    chunks_created: int
    files_skipped: int
    errors: list[str] = Field(default_factory=list)


class RAGSearchResult(BaseModel):
    id: str
    doc_type: str
    text: str
    metadata: dict | None = None
    score: float = Field(description="Similarity score (0-1, higher is better)")
    created_at: str | None = None


class RAGSearchResponse(BaseModel):
    results: list[RAGSearchResult] = Field(default_factory=list)
    query: str
    total: int = Field(description="Number of results returned")
