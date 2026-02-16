import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from kitchen_pilot.services.llm import stream_chat_completion

router = APIRouter(tags=["chat"])

SYSTEM_PROMPT = (
    "You are Kitchen Pilot, a friendly meal planning assistant. "
    "Help users plan weekly meals, suggest recipes, and answer cooking questions. "
    "Be concise and practical."
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[dict[str, str]] = Field(default_factory=list)


async def _stream_response(messages: list[dict[str, str]]) -> AsyncGenerator[str, None]:
    async for content in stream_chat_completion(messages):
        yield json.dumps({"content": content})


@router.post("/chat")
async def chat(request: ChatRequest) -> EventSourceResponse:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(request.history)
    messages.append({"role": "user", "content": request.message})

    return EventSourceResponse(_stream_response(messages))
