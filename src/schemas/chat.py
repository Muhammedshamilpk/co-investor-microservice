"""
Pydantic schemas for the Chat API request/response cycle.
All public API shapes live here — keep agents decoupled from HTTP concerns.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


# ── Intent ────────────────────────────────────────────────────────────────────

class IntentType(str, Enum):
    PORTFOLIO_HEALTH = "portfolio_health"
    MARKET_RESEARCH  = "market_research"
    GENERAL_QUERY    = "general_query"
    UNKNOWN          = "unknown"


class ExtractedEntities(BaseModel):
    tickers: list[str] = Field(default_factory=list)
    amounts: list[str] = Field(default_factory=list)
    time_periods: list[str] = Field(default_factory=list)


class IntentResult(BaseModel):
    intent: IntentType
    agent: str
    entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    safety: str = Field(default="safe")


# ── Chat ──────────────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=32_000)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(..., min_length=1)
    session_id: str | None = None
    stream: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    session_id: str
    intent: IntentResult
    content: str
    agent_used: str
    usage: dict[str, int] | None = None      # token counts when available


# ── Safety ────────────────────────────────────────────────────────────────────

class SafetyResult(BaseModel):
    blocked: bool
    category: str | None = None
    message: str | None = None


# ── Agent ─────────────────────────────────────────────────────────────────────

class AgentResponse(BaseModel):
    """Internal model returned by every agent."""
    content: str
    agent_name: str
    metadata: dict[str, Any] = Field(default_factory=dict)
