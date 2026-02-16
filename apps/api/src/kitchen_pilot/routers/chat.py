import json
from collections.abc import AsyncGenerator

import litellm
from fastapi import APIRouter
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from kitchen_pilot.config import settings

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
    response = await litellm.acompletion(
        model=settings.default_model,
        messages=messages,
        temperature=0.7,
        stream=True,
    )
    async for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield json.dumps({"content": delta.content})


@router.post("/chat")
async def chat(request: ChatRequest) -> EventSourceResponse:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(request.history)
    messages.append({"role": "user", "content": request.message})

    return EventSourceResponse(_stream_response(messages))
