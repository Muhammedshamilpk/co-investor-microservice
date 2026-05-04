"""
FastAPI dependencies.
Wire up the DI graph for controllers/routes.
"""

from typing import Annotated
from fastapi import Depends

from src.llm.client import BaseLLMClient, get_llm_client
from src.services.intent_classifier import IntentClassifier
from src.services.router import AgentRouter
from src.services.safety_guard import SafetyGuard


def get_safety_guard() -> SafetyGuard:
    return SafetyGuard()


def get_intent_classifier(
    llm: BaseLLMClient = Depends(get_llm_client),
) -> IntentClassifier:
    return IntentClassifier(llm_client=llm)


def get_agent_router(
    llm: BaseLLMClient = Depends(get_llm_client),
) -> AgentRouter:
    return AgentRouter(llm_client=llm)


# Type aliases for cleaner route signatures
SafetyDep = Annotated[SafetyGuard, Depends(get_safety_guard)]
IntentDep = Annotated[IntentClassifier, Depends(get_intent_classifier)]
RouterDep = Annotated[AgentRouter, Depends(get_agent_router)]
LLMDep = Annotated[BaseLLMClient, Depends(get_llm_client)]
