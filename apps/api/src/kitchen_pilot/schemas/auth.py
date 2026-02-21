"""Schemas for the auth router."""

from pydantic import BaseModel


class GoogleAuthStartResponse(BaseModel):
    authorization_url: str


class GoogleAuthStatusResponse(BaseModel):
    connected: bool
    scopes: list[str] | None = None
    token_expiry: str | None = None  # ISO datetime string


class GoogleDisconnectResponse(BaseModel):
    disconnected: bool
