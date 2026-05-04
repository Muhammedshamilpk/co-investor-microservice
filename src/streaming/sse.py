"""
SSE (Server-Sent Events) streaming utilities.

Provides:
  - sse_event()        : format a single SSE frame
  - stream_agent_sse() : async generator wrapping LLM stream → SSE frames
  - heartbeat_sse()    : keepalive generator to prevent proxy timeouts
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from src.core.config import get_settings
from src.core.logging import get_logger
from src.llm.client import BaseLLMClient
from src.schemas.chat import Message

log = get_logger(__name__)
settings = get_settings()


def sse_dict(data: str | dict, event: str = "message") -> dict:
    """Format a Server-Sent Events dictionary for sse-starlette."""
    if isinstance(data, dict):
        data = json.dumps(data)
    return {"event": event, "data": data}


async def stream_agent_sse(
    llm_client: BaseLLMClient,
    messages: list[Message],
    agent_name: str,
) -> AsyncIterator[dict]:
    """
    Streams LLM token chunks as SSE frames.
    Sends a [DONE] frame when the stream is complete.
    """
    yield sse_dict({"agent": agent_name, "status": "start"}, event="meta")

    token_count = 0
    async for token in llm_client.stream(messages):
        token_count += 1
        yield sse_dict({"token": token})

    log.info("sse_stream_complete", agent=agent_name, tokens=token_count)
    yield sse_dict({"status": "done", "agent": agent_name}, event="done")


async def heartbeat_sse(interval: float | None = None) -> AsyncIterator[dict]:
    """
    Yields SSE comment keepalives so proxies/load-balancers don't kill the connection.
    Run concurrently with stream_agent_sse using asyncio.
    """
    _interval = interval or settings.SSE_HEARTBEAT_INTERVAL
    while True:
        await asyncio.sleep(_interval)
        yield {"event": "ping", "data": "heartbeat"}
