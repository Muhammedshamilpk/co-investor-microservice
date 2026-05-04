"""
LLM-based Intent Classifier — determines the user's intent, target agent, and extracts entities.

Designed for ONE LLM call per request.
Handles follow-up queries by passing conversation history.
Never crashes; gracefully falls back to UNKNOWN intent if parsing fails.
"""

from __future__ import annotations

import json
import re

from src.core.logging import get_logger
from src.llm.client import BaseLLMClient
from src.schemas.chat import ExtractedEntities, IntentResult, IntentType, Message

log = get_logger(__name__)

_CLASSIFIER_SYSTEM_PROMPT = """You are the core intent router for Valura, a financial AI.
Analyze the conversation (especially the final message) to determine the user's current intent, assign a target agent, extract relevant entities, and flag obvious safety risks.

You MUST respond ONLY with a raw JSON object matching this schema exactly:
{
  "intent": "portfolio_health" | "market_research" | "general_query" | "unknown",
  "agent": "portfolio_health_agent" | "market_research_agent" | "stub_agent",
  "entities": {
    "tickers": ["AAPL", "TSLA"], // Extract stock tickers, currencies, etc.
    "amounts": ["$10,000", "50%"], // Financial amounts or percentages
    "time_periods": ["last 6 months", "Q3 2023"] // Time horizons
  },
  "safety": "safe" | "risky" // "risky" if it implies illegal advice or manipulation
}

Rules:
1. Context-Aware: If the user says "what about Apple?" or "buy 50 shares of that", look at the previous messages to determine the intent.
2. Output valid JSON only. Do not include markdown code blocks (e.g., ```json) or explanations.
3. If the request is highly ambiguous or outside financial bounds, use "unknown" intent and "stub_agent".
"""


class IntentClassifier:
    def __init__(self, llm_client: BaseLLMClient) -> None:
        self._llm = llm_client

    def _parse_json_safely(self, raw_text: str) -> dict:
        """Strips markdown blocks and attempts to parse JSON."""
        text = raw_text.strip()
        # Remove potential markdown formatting returned by LLMs
        text = re.sub(r"^```(json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text)

    async def classify(self, messages: list[Message]) -> IntentResult:
        """
        Classify intent and extract entities using a single LLM call.
        Sends recent conversation history to handle follow-up context.
        """
        # We send up to the last 6 messages to provide enough context for follow-ups
        # without blowing up the token budget.
        recent_context = messages[-6:]
        
        prompt_messages = [
            Message(role="system", content=_CLASSIFIER_SYSTEM_PROMPT),
            *recent_context
        ]

        raw = ""
        try:
            # We configure a temperature of 0.0 for maximum determinism
            raw = await self._llm.complete(prompt_messages, max_tokens=250, temperature=0.0)
            
            data = self._parse_json_safely(raw)
            result = IntentResult(**data)
            
            log.info(
                "intent_classified", 
                intent=result.intent.value, 
                agent=result.agent,
                safety=result.safety,
                entities_found=bool(
                    result.entities.tickers or 
                    result.entities.amounts or 
                    result.entities.time_periods
                )
            )
            return result

        except json.JSONDecodeError:
            log.error("intent_parse_failed_json", raw=raw)
        except Exception as e:
            log.error("intent_classification_error", error=str(e), raw=raw)

        # ── Fallback (Never Crash) ──
        return IntentResult(
            intent=IntentType.UNKNOWN,
            agent="stub_agent",
            entities=ExtractedEntities(),
            safety="unknown"
        )
