"""Voice router — STT and TTS endpoints."""

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from kitchen_pilot.schemas.voice import STTResponse, TTSRequest
from kitchen_pilot.services import voice as voice_svc
from kitchen_pilot.services.voice import ALLOWED_MIME_TYPES, MAX_FILE_SIZE

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/stt", response_model=STTResponse)
async def speech_to_text(file: UploadFile):
    """Transcribe uploaded audio to text via OpenAI Whisper."""
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {file.content_type}. "
            f"Supported: webm, wav, mp3, mp4, m4a, ogg, flac.",
        )

    audio_bytes = await file.read()
    if len(audio_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 25 MB)")
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    try:
        return await voice_svc.transcribe(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.webm",
            content_type=file.content_type or "audio/webm",
        )
    except voice_svc.VoiceServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    """Synthesize text to speech via OpenAI TTS API."""
    try:
        return StreamingResponse(
            voice_svc.synthesize(
                text=request.text,
                voice=request.voice,
                speed=request.speed,
            ),
            media_type="audio/mpeg",
            headers={"Content-Disposition": 'inline; filename="speech.mp3"'},
        )
    except voice_svc.VoiceServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
