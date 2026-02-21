"""Google Drive service.

Lists and downloads text content from Google Drive for recipe ingestion.
Uses the same OAuth tokens and patterns as calendar_service.py.
"""

import asyncio
import io
import logging
import uuid
from typing import Any

import pymupdf
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.ext.asyncio import AsyncSession

from kitchen_pilot.config import settings
from kitchen_pilot.services import token_service

logger = logging.getLogger(__name__)

DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.readonly"

GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
PLAIN_TEXT_MIME = "text/plain"
PDF_MIME = "application/pdf"
SUPPORTED_MIME_TYPES = {GOOGLE_DOC_MIME, PLAIN_TEXT_MIME, PDF_MIME}


class DriveServiceError(Exception):
    """Raised when a Drive operation fails."""


async def _execute(request: Any) -> Any:
    """Execute a Google API request in a thread to avoid blocking."""
    return await asyncio.to_thread(request.execute)


async def _get_drive_service(
    session: AsyncSession,
    household_id: uuid.UUID,
) -> Any:
    """Build an authenticated Google Drive API service object."""
    access_token = await token_service.get_valid_access_token(session, household_id)
    row = await token_service.get_tokens(session, household_id)

    if row and DRIVE_SCOPE not in (row.scopes or []):
        raise DriveServiceError(
            "Google Drive access not granted. "
            "Please reconnect Google with Drive permissions from your profile."
        )

    creds = Credentials(
        token=access_token,
        refresh_token=token_service.decrypt_token(row.encrypted_refresh_token),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
    )

    return await asyncio.to_thread(build, "drive", "v3", credentials=creds)


async def is_available(
    session: AsyncSession,
    household_id: uuid.UUID,
) -> bool:
    """Check if Google Drive is connected with read scope."""
    row = await token_service.get_tokens(session, household_id)
    if row is None:
        return False
    return DRIVE_SCOPE in (row.scopes or [])


async def list_files(
    session: AsyncSession,
    household_id: uuid.UUID,
    folder_id: str | None = None,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    """List Google Drive files that can be ingested."""
    service = await _get_drive_service(session, household_id)

    mime_filter = " or ".join(f"mimeType='{m}'" for m in SUPPORTED_MIME_TYPES)
    q = f"({mime_filter}) and trashed=false"
    if folder_id:
        q += f" and '{folder_id}' in parents"

    fields = "files(id, name, mimeType, modifiedTime, webViewLink)"
    result = await _execute(
        service.files().list(q=q, pageSize=page_size, fields=fields)
    )
    return result.get("files", [])


async def get_file_text(
    session: AsyncSession,
    household_id: uuid.UUID,
    file_id: str,
    mime_type: str,
) -> str:
    """Download a file's text content from Google Drive."""
    service = await _get_drive_service(session, household_id)

    if mime_type == GOOGLE_DOC_MIME:
        content = await _execute(
            service.files().export(fileId=file_id, mimeType="text/plain")
        )
    elif mime_type in (PLAIN_TEXT_MIME, PDF_MIME):
        content = await _execute(
            service.files().get_media(fileId=file_id)
        )
    else:
        raise DriveServiceError(f"Unsupported MIME type: {mime_type}")

    if mime_type == PDF_MIME:
        pdf_bytes = content if isinstance(content, bytes) else content.encode("utf-8")
        return await asyncio.to_thread(_extract_pdf_text, pdf_bytes)

    if isinstance(content, bytes):
        return content.decode("utf-8")
    return content


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using pymupdf."""
    doc = pymupdf.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)
