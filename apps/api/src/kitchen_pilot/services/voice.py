"""Voice service — STT (Whisper) and TTS (OpenAI).

Uses OpenAI APIs directly via httpx for simplicity.
"""

import logging
from collections.abc import AsyncIterator

import httpx

from kitchen_pilot.config import settings
from kitchen_pilot.schemas.voice import STTResponse

logger = logging.getLogger(__name__)

OPENAI_API_BASE = "https://api.openai.com/v1"

ALLOWED_MIME_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mp3",
    "audio/mpeg",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/ogg",
    "audio/flac",
    "audio/mpga",
}

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


class VoiceServiceError(Exception):
    """Raised when a voice operation fails."""


async def transcribe(
    audio_bytes: bytes,
    filename: str,
    content_type: str,
) -> STTResponse:
    """Transcribe audio to text using OpenAI Whisper API."""
    if not settings.openai_api_key:
        raise VoiceServiceError("OPENAI_API_KEY is not configured")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OPENAI_API_BASE}/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            files={"file": (filename, audio_bytes, content_type)},
            data={
                "model": settings.whisper_model,
                "response_format": "verbose_json",
            },
        )

    if response.status_code != 200:
        detail = response.json().get("error", {}).get("message", response.text)
        logger.error("Whisper API error: %s", detail)
        raise VoiceServiceError(f"Transcription failed: {detail}")

    data = response.json()
    return STTResponse(
        text=data.get("text", ""),
        language=data.get("language"),
    )


async def synthesize(
    text: str,
    voice: str | None = None,
    speed: float = 1.0,
) -> AsyncIterator[bytes]:
    """Synthesize text to speech using OpenAI TTS API.

    Yields audio chunks (mp3) as they arrive.
    """
    if not settings.openai_api_key:
        raise VoiceServiceError("OPENAI_API_KEY is not configured")

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            f"{OPENAI_API_BASE}/audio/speech",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "tts-1",
                "input": text,
                "voice": voice or settings.tts_voice,
                "response_format": "mp3",
                "speed": speed,
            },
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                logger.error("TTS API error: %s", body.decode())
                raise VoiceServiceError("Speech synthesis failed")
            async for chunk in response.aiter_bytes(chunk_size=4096):
                yield chunk
