import logging
import os
from collections.abc import AsyncGenerator

import instructor
import litellm
from pydantic import BaseModel

from kitchen_pilot.config import settings

logger = logging.getLogger(__name__)

# Configure LiteLLM defaults
litellm.drop_params = True

# Expose OpenAI key to litellm if configured
if settings.openai_api_key:
    os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)

# Build instructor client wrapping async litellm
# Use JSON mode instead of tool calling — local Ollama models don't reliably
# produce tool_calls but handle JSON output well.
client = instructor.from_litellm(litellm.acompletion, mode=instructor.Mode.JSON)

# Model escalation chain: try each in order until one succeeds
MODEL_CHAIN = [settings.default_model, *settings.fallback_models]


def _api_base_for_model(model: str) -> str | None:
    """Return api_base only for Ollama models; OpenAI/cloud models need no override."""
    if model.startswith("ollama"):
        return settings.ollama_base_url
    return None


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
            logger.info("Trying model %s for %s", m, response_model.__name__)
            kwargs: dict = dict(
                model=m,
                messages=messages,
                response_model=response_model,
                max_retries=max_retries,
                temperature=temperature,
            )
            if base := _api_base_for_model(m):
                kwargs["api_base"] = base
            return await client.chat.completions.create(**kwargs)
        except Exception as e:
            logger.warning("Model %s failed for %s: %s", m, response_model.__name__, e)
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
    m = model or settings.default_model
    kwargs: dict = dict(
        model=m,
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    if base := _api_base_for_model(m):
        kwargs["api_base"] = base
    response = await litellm.acompletion(**kwargs)
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
    m = model or settings.default_model
    kwargs: dict = dict(
        model=m,
        messages=messages,
        temperature=temperature,
    )
    if base := _api_base_for_model(m):
        kwargs["api_base"] = base
    response = await litellm.acompletion(**kwargs)
    return response.choices[0].message.content or ""
