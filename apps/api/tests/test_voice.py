"""Tests for voice endpoints and service."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from kitchen_pilot.routers.voice import router
from kitchen_pilot.schemas.voice import STTResponse, TTSRequest
from kitchen_pilot.services.voice import ALLOWED_MIME_TYPES, MAX_FILE_SIZE

app = FastAPI()
app.include_router(router)
client = TestClient(app)


# ── Schema tests ─────────────────────────────────────────


class TestVoiceSchemas:
    def test_stt_response(self):
        r = STTResponse(text="hello world", language="en")
        assert r.text == "hello world"
        assert r.language == "en"

    def test_stt_response_no_language(self):
        r = STTResponse(text="hello")
        assert r.language is None

    def test_tts_request_defaults(self):
        r = TTSRequest(text="hello")
        assert r.voice == "nova"
        assert r.speed == 1.0

    def test_tts_request_custom(self):
        r = TTSRequest(text="hello", voice="alloy", speed=1.5)
        assert r.voice == "alloy"
        assert r.speed == 1.5

    def test_tts_request_speed_bounds(self):
        with pytest.raises(Exception):
            TTSRequest(text="hello", speed=0.1)
        with pytest.raises(Exception):
            TTSRequest(text="hello", speed=5.0)

    def test_tts_request_empty_text(self):
        with pytest.raises(Exception):
            TTSRequest(text="")


# ── Constants tests ──────────────────────────────────────


class TestVoiceConstants:
    def test_allowed_mime_types(self):
        assert "audio/webm" in ALLOWED_MIME_TYPES
        assert "audio/wav" in ALLOWED_MIME_TYPES
        assert "audio/mp3" in ALLOWED_MIME_TYPES
        assert "audio/mpeg" in ALLOWED_MIME_TYPES
        assert "audio/ogg" in ALLOWED_MIME_TYPES

    def test_max_file_size(self):
        assert MAX_FILE_SIZE == 25 * 1024 * 1024


# ── STT endpoint tests ───────────────────────────────────


class TestSTTEndpoint:
    def test_rejects_unsupported_mime(self):
        response = client.post(
            "/voice/stt",
            files={"file": ("test.txt", b"not audio", "text/plain")},
        )
        assert response.status_code == 400
        assert "Unsupported audio format" in response.json()["detail"]

    def test_rejects_empty_file(self):
        response = client.post(
            "/voice/stt",
            files={"file": ("test.webm", b"", "audio/webm")},
        )
        assert response.status_code == 400
        assert "Empty" in response.json()["detail"]

    @patch("kitchen_pilot.routers.voice.voice_svc.transcribe", new_callable=AsyncMock)
    def test_successful_transcription(self, mock_transcribe):
        mock_transcribe.return_value = STTResponse(text="hello world", language="en")
        response = client.post(
            "/voice/stt",
            files={"file": ("test.webm", b"fake audio data", "audio/webm")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "hello world"
        assert data["language"] == "en"
        mock_transcribe.assert_called_once()

    @patch("kitchen_pilot.routers.voice.voice_svc.transcribe", new_callable=AsyncMock)
    def test_transcription_error(self, mock_transcribe):
        from kitchen_pilot.services.voice import VoiceServiceError

        mock_transcribe.side_effect = VoiceServiceError("API error")
        response = client.post(
            "/voice/stt",
            files={"file": ("test.webm", b"fake audio data", "audio/webm")},
        )
        assert response.status_code == 500
        assert "API error" in response.json()["detail"]


# ── TTS endpoint tests ───────────────────────────────────


class TestTTSEndpoint:
    @patch("kitchen_pilot.routers.voice.voice_svc.synthesize")
    def test_successful_tts(self, mock_synthesize):
        async def fake_stream(*_args, **_kwargs):
            yield b"fake mp3 data"

        mock_synthesize.return_value = fake_stream()
        response = client.post(
            "/voice/tts",
            json={"text": "hello world"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mpeg"
        assert len(response.content) > 0

    def test_tts_empty_text(self):
        response = client.post(
            "/voice/tts",
            json={"text": ""},
        )
        assert response.status_code == 422

    def test_tts_custom_voice(self):
        with patch("kitchen_pilot.routers.voice.voice_svc.synthesize") as mock:
            async def fake_stream(*_args, **_kwargs):
                yield b"audio"

            mock.return_value = fake_stream()
            response = client.post(
                "/voice/tts",
                json={"text": "hello", "voice": "alloy", "speed": 1.5},
            )
            assert response.status_code == 200
