from collections.abc import AsyncGenerator

import instructor
import litellm
from pydantic import BaseModel

from kitchen_pilot.config import settings

# Configure LiteLLM defaults
litellm.drop_params = True

# Build instructor client wrapping async litellm
client = instructor.from_litellm(litellm.acompletion)

# Model escalation chain: try each in order until one succeeds
MODEL_CHAIN = [settings.default_model, *settings.fallback_models]


async def generate_structured[T: BaseModel](
    response_model: type[T],
    messages: list[dict[str, str]],
    model: str | None = None,
    max_retries: int = 3,
    temperature: float = 0,
) -> T:
    """Generate a structured Pydantic object from an LLM call.

    Uses instructor for automatic validation + retry. Falls back through the
    model chain if the primary model fails.
    """
    models = [model] if model else MODEL_CHAIN

    last_error: Exception | None = None
    for m in models:
        try:
            return await client(
                model=m,
                messages=messages,
                response_model=response_model,
                max_retries=max_retries,
                temperature=temperature,
                api_base=settings.ollama_base_url,
            )
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(
        f"All models failed for {response_model.__name__}. Last error: {last_error}"
    )


async def stream_chat_completion(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.7,
) -> AsyncGenerator[str, None]:
    """Stream chat completion tokens. Yields content strings."""
    response = await litellm.acompletion(
        model=model or settings.default_model,
        messages=messages,
        temperature=temperature,
        stream=True,
        api_base=settings.ollama_base_url,
    )
    async for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


async def chat_completion(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.7,
) -> str:
    """Simple unstructured chat completion for the chat endpoint."""
    response = await litellm.acompletion(
        model=model or settings.default_model,
        messages=messages,
        temperature=temperature,
        api_base=settings.ollama_base_url,
    )
    return response.choices[0].message.content or ""
