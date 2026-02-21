"""Google OAuth 2.0 router.

Handles the authorization flow, token exchange, connection status,
and disconnection for Google Calendar integration.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from kitchen_pilot.config import settings
from kitchen_pilot.db.engine import get_session
from kitchen_pilot.dependencies import get_household_id
from kitchen_pilot.schemas.auth import (
    GoogleAuthStartResponse,
    GoogleAuthStatusResponse,
    GoogleDisconnectResponse,
)
from kitchen_pilot.services import token_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"
DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
ALL_SCOPES = [CALENDAR_SCOPE, DRIVE_READONLY_SCOPE]


@router.get("/google/start", response_model=GoogleAuthStartResponse)
async def google_auth_start(
    household_id: uuid.UUID = Depends(get_household_id),  # noqa: B008
):
    """Return the Google OAuth authorization URL."""
    if not settings.google_oauth_client_id:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth is not configured (missing GOOGLE_OAUTH_CLIENT_ID).",
        )

    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": settings.google_oauth_redirect_url,
        "response_type": "code",
        "scope": " ".join(ALL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    authorization_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return GoogleAuthStartResponse(authorization_url=authorization_url)


@router.get("/google/callback")
async def google_auth_callback(
    code: str,
    state: str | None = None,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    household_id: uuid.UUID = Depends(get_household_id),  # noqa: B008
):
    """Exchange the authorization code for tokens and redirect to frontend."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": settings.google_oauth_redirect_url,
                "grant_type": "authorization_code",
            },
        )

    if resp.status_code != 200:
        logger.error("Google token exchange failed: %s %s", resp.status_code, resp.text)
        raise HTTPException(
            status_code=400,
            detail="Failed to exchange authorization code with Google.",
        )

    data = resp.json()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    expires_in = data.get("expires_in", 3600)

    if not access_token or not refresh_token:
        raise HTTPException(
            status_code=400,
            detail="Google did not return expected tokens.",
        )

    token_expiry = datetime.now(UTC) + timedelta(seconds=expires_in)

    await token_service.store_tokens(
        session=session,
        household_id=household_id,
        provider=token_service.GOOGLE_PROVIDER,
        access_token=access_token,
        refresh_token=refresh_token,
        token_expiry=token_expiry,
        scopes=ALL_SCOPES,
    )

    logger.info("Google OAuth tokens stored for household %s", household_id)
    return RedirectResponse(url=f"{settings.frontend_url}/profile?google=connected")


@router.get("/google/status", response_model=GoogleAuthStatusResponse)
async def google_auth_status(
    session: AsyncSession = Depends(get_session),  # noqa: B008
    household_id: uuid.UUID = Depends(get_household_id),  # noqa: B008
):
    """Check if Google Calendar is connected."""
    row = await token_service.get_tokens(session, household_id)
    if row is None:
        return GoogleAuthStatusResponse(connected=False)
    return GoogleAuthStatusResponse(
        connected=True,
        scopes=row.scopes,
        token_expiry=row.token_expiry.isoformat() if row.token_expiry else None,
    )


@router.post("/google/disconnect", response_model=GoogleDisconnectResponse)
async def google_auth_disconnect(
    session: AsyncSession = Depends(get_session),  # noqa: B008
    household_id: uuid.UUID = Depends(get_household_id),  # noqa: B008
):
    """Revoke and delete stored Google tokens."""
    row = await token_service.get_tokens(session, household_id)
    if row:
        # Best-effort revocation
        try:
            access_token = token_service.decrypt_token(row.encrypted_access_token)
            async with httpx.AsyncClient() as client:
                await client.post(
                    GOOGLE_REVOKE_URL,
                    params={"token": access_token},
                )
        except Exception as e:
            logger.warning("Google token revocation failed (non-fatal): %s", e)

    deleted = await token_service.delete_tokens(session, household_id)
    return GoogleDisconnectResponse(disconnected=deleted)
