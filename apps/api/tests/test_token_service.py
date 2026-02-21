"""Tests for the token service."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kitchen_pilot.services import token_service


@pytest.fixture(autouse=True)
def _set_fernet_key():
    """Provide a valid Fernet key for all tests."""
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    with patch.object(token_service.settings, "fernet_key", key):
        yield


def test_encrypt_decrypt_roundtrip():
    plaintext = "my-secret-token-12345"
    encrypted = token_service.encrypt_token(plaintext)
    assert encrypted != plaintext.encode()
    decrypted = token_service.decrypt_token(encrypted)
    assert decrypted == plaintext


def test_encrypt_different_each_time():
    """Fernet includes a timestamp, so each encryption differs."""
    plaintext = "same-value"
    a = token_service.encrypt_token(plaintext)
    b = token_service.encrypt_token(plaintext)
    assert a != b
    # But both decrypt to the same value
    assert token_service.decrypt_token(a) == plaintext
    assert token_service.decrypt_token(b) == plaintext


def test_get_fernet_raises_when_unconfigured():
    with patch.object(token_service.settings, "fernet_key", ""):
        with pytest.raises(RuntimeError, match="FERNET_KEY is not configured"):
            token_service._get_fernet()


@pytest.mark.asyncio
async def test_get_tokens_returns_none_when_empty():
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session.execute.return_value = result_mock

    result = await token_service.get_tokens(session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_delete_tokens_returns_false_when_no_row():
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session.execute.return_value = result_mock

    deleted = await token_service.delete_tokens(session, uuid.uuid4())
    assert deleted is False


@pytest.mark.asyncio
async def test_get_valid_access_token_raises_when_no_tokens():
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session.execute.return_value = result_mock

    with pytest.raises(ValueError, match="No google tokens stored"):
        await token_service.get_valid_access_token(session, uuid.uuid4())


@pytest.mark.asyncio
async def test_get_valid_access_token_returns_when_not_expired():
    household_id = uuid.uuid4()
    access_token = "valid-access-token"
    encrypted = token_service.encrypt_token(access_token)

    row = MagicMock()
    row.encrypted_access_token = encrypted
    row.token_expiry = datetime.now(UTC) + timedelta(hours=1)

    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = row
    session.execute.return_value = result_mock

    result = await token_service.get_valid_access_token(session, household_id)
    assert result == access_token
