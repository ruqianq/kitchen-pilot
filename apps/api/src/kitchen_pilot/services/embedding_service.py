"""Embedding service.

Generates text embeddings using litellm (OpenAI text-embedding-3-small)
and handles document chunking for RAG ingestion.
"""

import logging
import os

import litellm

from kitchen_pilot.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_SIZE = 4000  # characters (~1000 tokens)
CHUNK_OVERLAP = 200  # characters overlap between chunks

# Ensure OpenAI key is available (mirrors pattern from llm.py)
if settings.openai_api_key:
    os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping chunks.

    Short texts (< chunk_size) return as a single chunk.
    Empty texts return an empty list.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
    return chunks


async def generate_embedding(text: str) -> list[float]:
    """Generate a 1536-dim embedding vector for a text string."""
    try:
        response = await litellm.aembedding(
            model=EMBEDDING_MODEL,
            input=[text],
        )
        return response.data[0]["embedding"]
    except Exception as e:
        logger.error("Embedding generation failed: %s", e)
        raise RuntimeError(f"Failed to generate embedding: {e}") from e


async def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts in a single API call."""
    if not texts:
        return []
    try:
        response = await litellm.aembedding(
            model=EMBEDDING_MODEL,
            input=texts,
        )
        sorted_data = sorted(response.data, key=lambda x: x["index"])
        return [item["embedding"] for item in sorted_data]
    except Exception as e:
        logger.error("Batch embedding generation failed: %s", e)
        raise RuntimeError(f"Failed to generate embeddings: {e}") from e
