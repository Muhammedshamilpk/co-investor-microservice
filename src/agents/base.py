"""
BaseAgent — contract every agent must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.llm.client import BaseLLMClient
from src.schemas.chat import AgentResponse, Message


class BaseAgent(ABC):
    def __init__(self, name: str, llm_client: BaseLLMClient) -> None:
        self.name = name
        self._llm = llm_client

    @abstractmethod
    async def run(self, messages: list[Message]) -> AgentResponse:
        """Execute agent logic and return a structured response."""
        ...
