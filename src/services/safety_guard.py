"""
High-performance pure Python safety guard for financial queries.
Zero network calls, zero LLMs, sub-10ms execution via compiled regexes.

Categories covered:
- Insider trading
- Market manipulation
- Guaranteed returns
- Illegal financial advice
"""

from __future__ import annotations

import re

from src.core.logging import get_logger
from src.schemas.chat import SafetyResult

log = get_logger(__name__)


class SafetyGuard:
    def __init__(self) -> None:
        # 1. Educational overrides: These patterns bypass the strict blocking.
        # We want to allow queries like "What is insider trading?" or "Explain market manipulation"
        # but NOT "Explain how to do insider trading".
        self._educational_patterns = [
            re.compile(
                r"^(what\s+(is|are)|explain|define|meaning\s+of|tell\s+me\s+about|describe)\s+(?!how\s+to\s+)",
                re.IGNORECASE,
            ),
        ]

        # 2. Harmful patterns mapped to categories
        self._block_patterns: dict[str, list[re.Pattern]] = {
            "insider_trading": [
                re.compile(r"\b(non-public|nonpublic|confidential|insider)\b.*\b(info|information|tip|tips|advice)\b", re.IGNORECASE),
                re.compile(r"\btrade\b.*\bbased\s+on\b.*\b(leaked|unreleased|internal)\b", re.IGNORECASE),
                re.compile(r"\b(friend|uncle|ceo|executive|source)\b.*\btold\s+me\b.*\bbuy\b", re.IGNORECASE),
            ],

            "market_manipulation": [
                re.compile(r"\b(pump\s*(and|&)\s*dump|short\s*squeeze|spoofing|wash\s*trading)\b", re.IGNORECASE),
                re.compile(r"\b(manipulate|corner)\b.*\b(market|stock|price)\b", re.IGNORECASE),
                re.compile(r"\bcoordinate\b.*\b(buying|selling|dumping)\b", re.IGNORECASE),
            ],
            "guaranteed_returns": [
                re.compile(r"\b(guaranteed|risk-free|100%\s*return)\b", re.IGNORECASE),
                re.compile(r"\b(can't\s*lose|sure\s*thing|get\s*rich\s*quick)\b", re.IGNORECASE),
                re.compile(r"\bzero\s*risk\b", re.IGNORECASE),
            ],
            "illegal_financial_advice": [
                re.compile(r"\b(what\s*should\s*i\s*buy|tell\s*me\s*what\s*to\s*trade)\b", re.IGNORECASE),
                re.compile(r"\b(promise|assure)\b.*\b(profit|gains|returns)\b", re.IGNORECASE),
                re.compile(r"\b(should\s+i\s+invest\s+in)\b.*(now|today)\b", re.IGNORECASE),
            ],
        }

    async def check(self, user_message: str) -> SafetyResult:
        """
        Executes in <1ms. Checks for educational overrides first, then evaluates blocklists.
        """
        text = user_message.strip()

        if not text:
            return SafetyResult(blocked=False)

        # 1. Check Educational Overrides
        is_educational = False
        # Do not override if they are asking for instructions ("how to")
        if not re.search(r"\bhow\s+to\b", text, re.IGNORECASE):
            for edu_pattern in self._educational_patterns:
                if edu_pattern.search(text):
                    is_educational = True
                    break

        if is_educational:
            log.debug("safety_educational_override", text=text)
            return SafetyResult(blocked=False)

        # 2. Check Strict Blocklists
        for category, patterns in self._block_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    log.warning("safety_block_hit", category=category, pattern=pattern.pattern)
                    return SafetyResult(
                        blocked=True,
                        category=category,
                        message=f"Request blocked due to financial safety policy violation: {category.replace('_', ' ').title()}.",
                    )

        return SafetyResult(blocked=False)
