"""OAuth token service.

Handles Fernet encryption/decryption, CRUD operations on the oauth_tokens
table, and automatic Google token refresh.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kitchen_pilot.config import settings
from kitchen_pilot.db.models import OAuthToken

logger = logging.getLogger(__name__)

GOOGLE_PROVIDER = "google"


def _get_fernet() -> Fernet:
    """Return a Fernet instance from settings.fernet_key."""
    if not settings.fernet_key:
        raise RuntimeError(
            "FERNET_KEY is not configured. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(settings.fernet_key.encode())


def encrypt_token(plaintext: str) -> bytes:
    """Encrypt a token string to bytes."""
    return _get_fernet().encrypt(plaintext.encode())


def decrypt_token(ciphertext: bytes) -> str:
    """Decrypt bytes back to a token string."""
    return _get_fernet().decrypt(ciphertext).decode()


async def store_tokens(
    session: AsyncSession,
    household_id: uuid.UUID,
    provider: str,
    access_token: str,
    refresh_token: str,
    token_expiry: datetime,
    scopes: list[str],
) -> OAuthToken:
    """Store (or update) encrypted tokens for a household + provider."""
    stmt = select(OAuthToken).where(
        OAuthToken.household_id == household_id,
        OAuthToken.provider == provider,
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()

    encrypted_access = encrypt_token(access_token)
    encrypted_refresh = encrypt_token(refresh_token)

    if row:
        row.encrypted_access_token = encrypted_access
        row.encrypted_refresh_token = encrypted_refresh
        row.token_expiry = token_expiry
        row.scopes = scopes
    else:
        row = OAuthToken(
            household_id=household_id,
            provider=provider,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            token_expiry=token_expiry,
            scopes=scopes,
        )
        session.add(row)

    await session.commit()
    await session.refresh(row)
    return row


async def get_tokens(
    session: AsyncSession,
    household_id: uuid.UUID,
    provider: str = GOOGLE_PROVIDER,
) -> OAuthToken | None:
    """Retrieve the token row for a household + provider."""
    stmt = select(OAuthToken).where(
        OAuthToken.household_id == household_id,
        OAuthToken.provider == provider,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_valid_access_token(
    session: AsyncSession,
    household_id: uuid.UUID,
    provider: str = GOOGLE_PROVIDER,
) -> str:
    """Get a decrypted, valid access token — refreshing if expired.

    Raises ValueError if no tokens stored or refresh fails.
    """
    row = await get_tokens(session, household_id, provider)
    if row is None:
        raise ValueError(f"No {provider} tokens stored for household {household_id}")

    access_token = decrypt_token(row.encrypted_access_token)

    # If token still valid (with 5-minute buffer), return it
    if row.token_expiry > datetime.now(UTC) + timedelta(minutes=5):
        return access_token

    # Refresh the token
    logger.info("Refreshing expired %s token for household %s", provider, household_id)
    refresh_token = decrypt_token(row.encrypted_refresh_token)

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret,
        )

        await asyncio.to_thread(creds.refresh, Request())

        new_access = creds.token
        new_expiry = creds.expiry or (datetime.now(UTC) + timedelta(hours=1))
        if new_expiry.tzinfo is None:
            new_expiry = new_expiry.replace(tzinfo=UTC)

        # Update DB
        row.encrypted_access_token = encrypt_token(new_access)
        row.token_expiry = new_expiry
        await session.commit()
        await session.refresh(row)

        logger.info("Token refreshed for household %s", household_id)
        return new_access
    except Exception as e:
        raise ValueError(f"Failed to refresh {provider} token: {e}") from e


async def delete_tokens(
    session: AsyncSession,
    household_id: uuid.UUID,
    provider: str = GOOGLE_PROVIDER,
) -> bool:
    """Delete tokens for a household + provider. Returns True if deleted."""
    row = await get_tokens(session, household_id, provider)
    if row is None:
        return False
    await session.delete(row)
    await session.commit()
    return True
