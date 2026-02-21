"""Tests for RAG services: embedding chunking, search, and drive availability."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kitchen_pilot.services import embedding_service, rag_service
from kitchen_pilot.services.drive_service import DRIVE_SCOPE


# ── chunk_text ────────────────────────────────────────────


def test_chunk_text_short():
    """Text shorter than chunk_size returns a single chunk."""
    result = embedding_service.chunk_text("Hello world", chunk_size=100)
    assert result == ["Hello world"]


def test_chunk_text_long():
    """Long text gets split into overlapping chunks."""
    text = "A" * 500
    chunks = embedding_service.chunk_text(text, chunk_size=200, overlap=50)
    assert len(chunks) > 1
    # Each chunk should be at most chunk_size characters
    for chunk in chunks:
        assert len(chunk) <= 200
    # Full text should be reconstructable (all parts covered)
    combined_length = sum(len(c) for c in chunks)
    assert combined_length >= len(text)


def test_chunk_text_empty():
    """Empty or whitespace-only text returns empty list."""
    assert embedding_service.chunk_text("") == []
    assert embedding_service.chunk_text("   ") == []


def test_chunk_text_exact_size():
    """Text exactly at chunk_size returns a single chunk."""
    text = "B" * 200
    result = embedding_service.chunk_text(text, chunk_size=200)
    assert result == [text]


# ── search ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_empty_query():
    """Empty query returns empty list without calling embedding service."""
    session = AsyncMock()
    result = await rag_service.search(session, "00000000-0000-0000-0000-000000000000", "   ")
    assert result == []


# ── drive_service.is_available ────────────────────────────


@pytest.mark.asyncio
async def test_drive_is_available_true():
    """Returns True when tokens exist with Drive scope."""
    session = AsyncMock()
    mock_row = MagicMock()
    mock_row.scopes = [
        "https://www.googleapis.com/auth/calendar",
        DRIVE_SCOPE,
    ]

    with patch(
        "kitchen_pilot.services.drive_service.token_service.get_tokens",
        new_callable=AsyncMock,
        return_value=mock_row,
    ):
        from kitchen_pilot.services import drive_service

        result = await drive_service.is_available(session, "00000000-0000-0000-0000-000000000000")
    assert result is True


@pytest.mark.asyncio
async def test_drive_is_available_false():
    """Returns False when no tokens exist."""
    session = AsyncMock()

    with patch(
        "kitchen_pilot.services.drive_service.token_service.get_tokens",
        new_callable=AsyncMock,
        return_value=None,
    ):
        from kitchen_pilot.services import drive_service

        result = await drive_service.is_available(session, "00000000-0000-0000-0000-000000000000")
    assert result is False


@pytest.mark.asyncio
async def test_drive_is_available_no_drive_scope():
    """Returns False when tokens exist but only have calendar scope."""
    session = AsyncMock()
    mock_row = MagicMock()
    mock_row.scopes = ["https://www.googleapis.com/auth/calendar"]

    with patch(
        "kitchen_pilot.services.drive_service.token_service.get_tokens",
        new_callable=AsyncMock,
        return_value=mock_row,
    ):
        from kitchen_pilot.services import drive_service

        result = await drive_service.is_available(session, "00000000-0000-0000-0000-000000000000")
    assert result is False


# ── generate_embedding ────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_embedding():
    """generate_embedding calls litellm and returns the embedding vector."""
    fake_embedding = [0.1] * 1536
    mock_response = MagicMock()
    mock_response.data = [{"embedding": fake_embedding, "index": 0}]

    with patch("kitchen_pilot.services.embedding_service.litellm.aembedding", new_callable=AsyncMock, return_value=mock_response):
        result = await embedding_service.generate_embedding("test text")
    assert result == fake_embedding


@pytest.mark.asyncio
async def test_generate_embeddings_batch():
    """generate_embeddings_batch returns embeddings in order."""
    fake_embeddings = [[0.1] * 1536, [0.2] * 1536]
    mock_response = MagicMock()
    mock_response.data = [
        {"embedding": fake_embeddings[1], "index": 1},
        {"embedding": fake_embeddings[0], "index": 0},
    ]

    with patch("kitchen_pilot.services.embedding_service.litellm.aembedding", new_callable=AsyncMock, return_value=mock_response):
        result = await embedding_service.generate_embeddings_batch(["text1", "text2"])
    # Should be sorted by index
    assert result == fake_embeddings


@pytest.mark.asyncio
async def test_generate_embeddings_batch_empty():
    """Empty input returns empty list without API call."""
    result = await embedding_service.generate_embeddings_batch([])
    assert result == []
