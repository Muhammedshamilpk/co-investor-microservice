"""
Agent Router — maps IntentType → concrete agent.

To add a new agent:
  1. Create src/agents/your_agent.py implementing BaseAgent
  2. Register it in AGENT_REGISTRY below
"""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.portfolio_health_agent import PortfolioHealthAgent
from src.agents.stub_agent import StubAgent
from src.core.exceptions import AgentNotFoundError
from src.core.logging import get_logger
from src.llm.client import BaseLLMClient
from src.schemas.chat import AgentResponse, IntentResult, IntentType, Message

log = get_logger(__name__)


class AgentRouter:
    def __init__(self, llm_client: BaseLLMClient) -> None:
        self._llm = llm_client
        self._registry: dict[IntentType, BaseAgent] = {
            IntentType.PORTFOLIO_HEALTH: PortfolioHealthAgent(llm_client),
            IntentType.MARKET_RESEARCH:  StubAgent("market_research", llm_client),
            IntentType.GENERAL_QUERY:    StubAgent("general_query", llm_client),
            IntentType.UNKNOWN:          StubAgent("fallback", llm_client),
        }

    async def route(
        self, intent: IntentResult, messages: list[Message]
    ) -> AgentResponse:
        agent = self._registry.get(intent.intent)
        if agent is None:
            raise AgentNotFoundError(
                message=f"No agent registered for intent: {intent.intent}",
            )
        log.info("routing_to_agent", agent=agent.name, intent=intent.intent)
        return await agent.run(messages)
