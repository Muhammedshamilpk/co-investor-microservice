"""
Stub Agent — placeholder for intents that don't have a real agent yet.

Use this while building new agents so the router never crashes.
Replace with a real implementation by subclassing BaseAgent.
"""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.core.logging import get_logger
from src.llm.client import BaseLLMClient
from src.schemas.chat import AgentResponse, Message

log = get_logger(__name__)

_STUB_SYSTEM_PROMPT = """You are Valura, a helpful financial AI assistant.
Answer the user's question helpfully and concisely.
If you don't know something, say so clearly — never fabricate data."""


class StubAgent(BaseAgent):
    """
    Generic fallback agent.
    Instantiate with a descriptive name so logs clearly show which intent hit it.

    Example:
        StubAgent("market_research", llm_client)
    """

    def __init__(self, intent_label: str, llm_client: BaseLLMClient) -> None:
        super().__init__(f"stub_{intent_label}", llm_client)
        self._intent_label = intent_label

    async def run(self, messages: list[Message]) -> AgentResponse:
        log.info("stub_agent_called", intent=self._intent_label)
        enriched = [Message(role="system", content=_STUB_SYSTEM_PROMPT)] + messages
        content = await self._llm.complete(enriched)
        return AgentResponse(
            content=content,
            agent_name=self.name,
            metadata={"stub": True, "intent_label": self._intent_label},
        )
