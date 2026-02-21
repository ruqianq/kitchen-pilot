"""Tests for the native calendar service."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kitchen_pilot.services import calendar_service


@pytest.mark.asyncio
async def test_is_available_true_when_tokens_exist():
    session = AsyncMock()
    household_id = uuid.uuid4()

    with patch.object(
        calendar_service.token_service,
        "get_tokens",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = MagicMock()  # non-None = connected
        result = await calendar_service.is_available(session, household_id)
        assert result is True


@pytest.mark.asyncio
async def test_is_available_false_when_no_tokens():
    session = AsyncMock()
    household_id = uuid.uuid4()

    with patch.object(
        calendar_service.token_service,
        "get_tokens",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = None
        result = await calendar_service.is_available(session, household_id)
        assert result is False
