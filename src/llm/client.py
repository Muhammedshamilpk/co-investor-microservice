"""
LLM abstraction layer.
All agents call this wrapper — never the SDK directly.
Swap providers by changing LLM_PROVIDER in config.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterator

import openai

from src.core.config import get_settings
from src.core.exceptions import LLMError, LLMTimeoutError
from src.core.logging import get_logger
from src.schemas.chat import Message

log = get_logger(__name__)
settings = get_settings()


# ── Base contract ─────────────────────────────────────────────────────────────

class BaseLLMClient(ABC):
    @abstractmethod
    async def complete(self, messages: list[Message], **kwargs) -> str: ...

    @abstractmethod
    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]: ...


# ── OpenAI implementation ─────────────────────────────────────────────────────

class OpenAIClient(BaseLLMClient):
    def __init__(self) -> None:
        self._client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    def _build_payload(self, messages: list[Message], **kwargs) -> dict:
        return {
            "model": kwargs.get("model", settings.OPENAI_MODEL),
            "messages": [m.model_dump() for m in messages],
            "temperature": kwargs.get("temperature", settings.LLM_TEMPERATURE),
            "max_tokens": kwargs.get("max_tokens", settings.LLM_MAX_TOKENS),
        }

    async def complete(self, messages: list[Message], **kwargs) -> str:
        payload = self._build_payload(messages, **kwargs)
        try:
            response = await asyncio.wait_for(
                self._client.chat.completions.create(**payload),
                timeout=settings.LLM_TIMEOUT_SECONDS,
            )
            return response.choices[0].message.content or ""
        except asyncio.TimeoutError as exc:
            raise LLMTimeoutError("LLM request timed out") from exc
        except openai.OpenAIError as exc:
            log.error("openai_error", error=str(exc))
            raise LLMError(f"OpenAI error: {exc}") from exc

    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        payload = self._build_payload(messages, **kwargs)
        try:
            async with self._client.chat.completions.stream(**payload) as stream:
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
        except openai.OpenAIError as exc:
            log.error("openai_stream_error", error=str(exc))
            raise LLMError(f"OpenAI stream error: {exc}") from exc


# ── Stub/Mock implementation for Demos ────────────────────────────────────────

class StubClient(BaseLLMClient):
    """Simulates AI streaming for testing/demos without API costs."""
    async def complete(self, messages: list[Message], **kwargs) -> str:
        return "This is a simulated response for demo purposes."

    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        response = (
            "I've analyzed the market data for your query. "
            "Based on current trends, the asset is showing strong support at current levels. "
            "Technical indicators suggest a healthy recovery in the short term, "
            "though I recommend monitoring the upcoming earnings report for a clearer outlook."
        )
        for word in response.split():
            yield word + " "
            await asyncio.sleep(0.1)  # Simulate human-like typing speed


# ── Factory ───────────────────────────────────────────────────────────────────

_CLIENTS: dict[str, type[BaseLLMClient]] = {
    "openai": OpenAIClient,
    "stub": StubClient,
}


def get_llm_client() -> BaseLLMClient:
    """Dependency-injectable LLM client factory."""
    provider = settings.LLM_PROVIDER.lower()
    if provider not in _CLIENTS:
        raise LLMError(f"Unknown LLM provider: {provider}")
    return _CLIENTS[provider]()
