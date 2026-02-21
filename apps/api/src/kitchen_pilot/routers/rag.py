"""RAG ingestion and search router."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from kitchen_pilot.db.engine import get_session
from kitchen_pilot.dependencies import get_household_id
from kitchen_pilot.schemas.rag import (
    DriveIngestRequest,
    DriveIngestResponse,
    RAGSearchResponse,
    RAGSearchResult,
)
from kitchen_pilot.services import drive_service, rag_service

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/ingest/drive", response_model=DriveIngestResponse)
async def ingest_drive(
    body: DriveIngestRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    household_id: uuid.UUID = Depends(get_household_id),  # noqa: B008
) -> DriveIngestResponse:
    """Ingest recipe documents from Google Drive into vector store."""
    available = await drive_service.is_available(session, household_id)
    if not available:
        raise HTTPException(
            status_code=400,
            detail=(
                "Google Drive is not connected. "
                "Please connect Google with Drive permissions from your profile."
            ),
        )

    stats = await rag_service.ingest_drive_documents(
        session, household_id, body.folder_id
    )
    return DriveIngestResponse(**stats)


@router.get("/search", response_model=RAGSearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(5, ge=1, le=20),
    offset: int = Query(0, ge=0),
    doc_type: str | None = Query(None),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    household_id: uuid.UUID = Depends(get_household_id),  # noqa: B008
) -> RAGSearchResponse:
    """Search memory documents by semantic similarity."""
    results = await rag_service.search(
        session, household_id, q, limit=limit, offset=offset, doc_type=doc_type
    )
    return RAGSearchResponse(
        results=[RAGSearchResult(**r) for r in results],
        query=q,
        total=len(results),
    )
