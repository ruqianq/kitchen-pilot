"""Request/response schemas for voice endpoints."""

from pydantic import BaseModel, Field


class STTResponse(BaseModel):
    text: str
    language: str | None = None


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    voice: str = Field(
        default="nova",
        description="Voice: alloy, echo, fable, onyx, nova, shimmer",
    )
    speed: float = Field(default=1.0, ge=0.25, le=4.0)
