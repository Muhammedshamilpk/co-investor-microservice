"""
Portfolio Health Analysis Agent.

Calculates real metrics using yfinance and pandas.
Uses the LLM to generate beginner-friendly observations and extract the portfolio.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pandas as pd
import yfinance as yf

from src.agents.base import BaseAgent
from src.core.logging import get_logger
from src.llm.client import BaseLLMClient
from src.schemas.chat import AgentResponse, Message

log = get_logger(__name__)


_EXTRACT_PROMPT = """You are a financial entity extractor. 
Analyze the user's messages and extract their current stock portfolio and percentage allocations.
Return ONLY valid JSON matching this schema:
{"portfolio": {"AAPL": 0.4, "MSFT": 0.6}}

If no portfolio is mentioned, or if it's completely empty, return:
{"portfolio": {}}

Rules:
- Ensure allocations sum to 1.0 (e.g., 50% = 0.5).
- If tickers are provided but allocations are not, distribute the percentages equally.
- ONLY output JSON. No markdown blocks.
"""

_OBSERVATIONS_PROMPT = """You are Valura, a beginner-friendly financial advisor.
Review the following calculated portfolio metrics:
{metrics}

Generate 3-4 simple, encouraging observations.
- Keep it extremely simple for beginners.
- Highlight key risks (like high concentration) or opportunities (like beating the S&P 500).
- Be polite and educational.
- Include a standard short financial disclaimer.

Return ONLY valid JSON matching this schema:
{{
  "observations": ["obs 1", "obs 2", "obs 3"],
  "disclaimer": "..."
}}
"""

_EMPTY_PORTFOLIO_ADVICE = {
    "concentration_risk": {},
    "performance": {},
    "benchmark_comparison": {},
    "observations": [
        "It looks like you haven't added any stocks to your portfolio yet!",
        "A great way to start investing is by looking into broad-market index funds like the S&P 500.",
        "Remember that investing is a marathon, not a sprint. Start small and stay consistent."
    ],
    "disclaimer": "This information is for educational purposes only and does not constitute financial advice."
}


class PortfolioHealthAgent(BaseAgent):
    def __init__(self, llm_client: BaseLLMClient) -> None:
        super().__init__("portfolio_health", llm_client)

    async def _extract_portfolio(self, messages: list[Message]) -> dict[str, float]:
        """Uses the LLM to parse the conversation into a portfolio dict."""
        context = messages[-4:]
        prompt_msgs = [Message(role="system", content=_EXTRACT_PROMPT)] + context
        
        raw = await self._llm.complete(prompt_msgs, temperature=0.0)
        
        try:
            cleaned = raw.strip().replace("```json", "").replace("```", "")
            data = json.loads(cleaned)
            return data.get("portfolio", {})
        except Exception as e:
            log.error("portfolio_extraction_failed", error=str(e), raw=raw)
            return {}

    def _fetch_market_data(self, tickers: list[str]) -> pd.DataFrame:
        """Fetch 1 year of historical data synchronously via yfinance."""
        symbols = tickers + ["^GSPC"]  # Always include S&P 500
        # yf.download with multiple tickers returns a DataFrame with a MultiIndex column or simple columns
        # Depending on yfinance version, we use progress=False
        try:
            data = yf.download(symbols, period="1y", progress=False)["Close"]
            if isinstance(data, pd.Series):
                data = data.to_frame()
            return data
        except Exception as e:
            log.error("yfinance_fetch_failed", error=str(e))
            raise

    def _calculate_metrics(self, portfolio: dict[str, float], data: pd.DataFrame) -> dict[str, Any]:
        """Calculates concentration, performance, and benchmark comparison."""
        metrics: dict[str, Any] = {}
        
        # 1. Concentration Risk
        sorted_allocs = sorted(portfolio.items(), key=lambda x: x[1], reverse=True)
        top_holding = sorted_allocs[0] if sorted_allocs else ("None", 0.0)
        top_3 = sum(alloc for _, alloc in sorted_allocs[:3])
        
        metrics["concentration_risk"] = {
            "top_position_pct": round(top_holding[1] * 100, 2),
            "top_3_positions_pct": round(top_3 * 100, 2),
            "flag": "high" if (top_holding[1] > 0.25 or top_3 > 0.50) else "normal"
        }
        
        # 2. Performance (1 Year)
        start_prices = data.iloc[0]
        end_prices = data.iloc[-1]
        returns = (end_prices - start_prices) / start_prices
        
        portfolio_return = 0.0
        for ticker, weight in portfolio.items():
            if ticker in returns:
                portfolio_return += float(returns[ticker]) * weight
                
        metrics["performance"] = {
            "total_return_pct": round(portfolio_return * 100, 2),
            "annualized_return_pct": round(portfolio_return * 100, 2)
        }
        
        # 3. Benchmark Comparison
        benchmark_return = float(returns.get("^GSPC", 0.0))
        metrics["benchmark_comparison"] = {
            "benchmark": "S&P 500",
            "portfolio_return_pct": round(portfolio_return * 100, 2),
            "benchmark_return_pct": round(benchmark_return * 100, 2),
            "alpha_pct": round((portfolio_return - benchmark_return) * 100, 2)
        }
        
        return metrics

    async def run(self, messages: list[Message]) -> AgentResponse:
        log.info("portfolio_health_agent_started")
        
        # 1. Extract
        portfolio = await self._extract_portfolio(messages)
        if not portfolio:
            return AgentResponse(
                content=json.dumps(_EMPTY_PORTFOLIO_ADVICE),
                agent_name=self.name
            )
            
        try:
            # 2. Fetch Data
            tickers = list(portfolio.keys())
            data = await asyncio.to_thread(self._fetch_market_data, tickers)
            
            # 3. Calculate Math
            metrics = await asyncio.to_thread(self._calculate_metrics, portfolio, data)
            
            # 4. Generate Observations
            obs_prompt = _OBSERVATIONS_PROMPT.format(metrics=json.dumps(metrics, indent=2))
            # Prompt update: return structured observations
            obs_prompt += "\nReturn observations as a list of objects: {\"severity\": \"warning\"|\"info\", \"text\": \"...\"}"
            
            raw_obs = await self._llm.complete([Message(role="system", content=obs_prompt)], temperature=0.3)
            
            cleaned_obs = raw_obs.strip().replace("```json", "").replace("```", "")
            obs_data = json.loads(cleaned_obs)
            
            # 5. Build Final Payload
            final_output = {
                "concentration_risk": metrics["concentration_risk"],
                "performance": metrics["performance"],
                "benchmark_comparison": metrics["benchmark_comparison"],
                "observations": obs_data.get("observations", []),
                "disclaimer": obs_data.get("disclaimer", "This is not investment advice. Always consult a professional.")
            }
            
            return AgentResponse(
                content=json.dumps(final_output),
                agent_name=self.name
            )
            
        except Exception as e:
            log.error("portfolio_agent_error", error=str(e))
            return AgentResponse(
                content=json.dumps({"error": "Failed to analyze portfolio.", "details": str(e)}),
                agent_name=self.name
            )
