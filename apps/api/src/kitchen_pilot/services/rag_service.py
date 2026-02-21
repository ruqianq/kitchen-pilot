"""RAG service.

Orchestrates document ingestion (Drive -> text -> chunks -> embeddings -> pgvector)
and similarity search over the memory_documents table.
"""

import logging
import uuid
from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from kitchen_pilot.db.models import MemoryDocument
from kitchen_pilot.services import drive_service, embedding_service

logger = logging.getLogger(__name__)

DOC_TYPE_DRIVE_RECIPE = "drive_recipe"


# ── Ingestion ────────────────────────────────────────────


async def ingest_drive_documents(
    session: AsyncSession,
    household_id: uuid.UUID,
    folder_id: str | None = None,
) -> dict[str, Any]:
    """Ingest recipe documents from Google Drive into pgvector.

    Pipeline: list files -> download text -> chunk -> embed -> store.
    Returns stats: {files_processed, chunks_created, files_skipped, errors}.
    """
    files = await drive_service.list_files(session, household_id, folder_id)

    stats: dict[str, Any] = {
        "files_processed": 0,
        "chunks_created": 0,
        "files_skipped": 0,
        "errors": [],
    }

    for file in files:
        file_id = file["id"]
        file_name = file["name"]
        mime_type = file["mimeType"]

        try:
            file_text = await drive_service.get_file_text(
                session, household_id, file_id, mime_type
            )

            if not file_text.strip():
                stats["files_skipped"] += 1
                continue

            chunks = embedding_service.chunk_text(file_text)
            if not chunks:
                stats["files_skipped"] += 1
                continue

            embeddings = await embedding_service.generate_embeddings_batch(chunks)

            # Delete existing chunks for this file (upsert semantics)
            await session.execute(
                delete(MemoryDocument).where(
                    MemoryDocument.household_id == household_id,
                    MemoryDocument.doc_type == DOC_TYPE_DRIVE_RECIPE,
                    MemoryDocument.metadata_json["drive_file_id"].as_string()
                    == file_id,
                )
            )

            for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                doc = MemoryDocument(
                    household_id=household_id,
                    doc_type=DOC_TYPE_DRIVE_RECIPE,
                    text=chunk_text,
                    metadata_json={
                        "drive_file_id": file_id,
                        "drive_file_name": file_name,
                        "mime_type": mime_type,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "web_view_link": file.get("webViewLink"),
                        "modified_time": file.get("modifiedTime"),
                    },
                    embedding=embedding,
                )
                session.add(doc)

            stats["files_processed"] += 1
            stats["chunks_created"] += len(chunks)

        except Exception as e:
            logger.warning(
                "Failed to ingest file %s (%s): %s", file_name, file_id, e
            )
            stats["errors"].append(f"{file_name}: {e!s}")

    await session.commit()
    return stats


# ── Search ───────────────────────────────────────────────


async def search(
    session: AsyncSession,
    household_id: uuid.UUID,
    query: str,
    limit: int = 5,
    offset: int = 0,
    doc_type: str | None = None,
) -> list[dict[str, Any]]:
    """Search memory documents by semantic similarity.

    Returns a list of dicts with: id, doc_type, text, metadata, score, created_at.
    """
    if not query.strip():
        return []

    query_embedding = await embedding_service.generate_embedding(query)

    stmt = (
        select(
            MemoryDocument.id,
            MemoryDocument.doc_type,
            MemoryDocument.text,
            MemoryDocument.metadata_json,
            MemoryDocument.created_at,
            MemoryDocument.embedding.cosine_distance(query_embedding).label(
                "distance"
            ),
        )
        .where(MemoryDocument.household_id == household_id)
        .where(MemoryDocument.embedding.is_not(None))
    )

    if doc_type:
        stmt = stmt.where(MemoryDocument.doc_type == doc_type)

    stmt = stmt.order_by("distance").offset(offset).limit(limit)

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            "id": str(row.id),
            "doc_type": row.doc_type,
            "text": row.text,
            "metadata": row.metadata_json,
            "score": round(1 - row.distance, 4),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
