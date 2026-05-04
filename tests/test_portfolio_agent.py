import json
import pytest
import pandas as pd
from src.agents.portfolio_health_agent import PortfolioHealthAgent
from src.schemas.chat import Message

@pytest.fixture
def portfolio_agent(mock_llm):
    return PortfolioHealthAgent(llm_client=mock_llm)

@pytest.fixture
def mock_yfinance_data():
    """Mock 1 year of market data for AAPL and S&P 500"""
    data = {
        "AAPL": [150.0, 160.0, 170.0, 180.0],
        "^GSPC": [4000.0, 4100.0, 4200.0, 4300.0]
    }
    return pd.DataFrame(data)

@pytest.mark.asyncio
async def test_portfolio_agent_empty_portfolio(portfolio_agent: PortfolioHealthAgent, mock_llm):
    # LLM extraction returns empty portfolio
    mock_llm.set_response(json.dumps({"portfolio": {}}))
    
    messages = [Message(role="user", content="How is my portfolio doing?")]
    response = await portfolio_agent.run(messages)
    
    assert response.agent_name == "portfolio_health"
    content = json.loads(response.content)
    assert "It looks like you haven't added any stocks" in content["observations"][0]

@pytest.mark.asyncio
async def test_portfolio_agent_with_data(portfolio_agent: PortfolioHealthAgent, mock_llm, mock_yfinance_data, monkeypatch):
    # Mock LLM portfolio extraction
    mock_llm.set_response(json.dumps({"portfolio": {"AAPL": 1.0}}))
    
    # Mock LLM observations generation
    mock_llm.set_response(json.dumps({
        "observations": ["Your AAPL holding is doing well.", "High concentration risk."],
        "disclaimer": "Test disclaimer"
    }))
    
    # Mock yfinance data fetch
    monkeypatch.setattr(PortfolioHealthAgent, "_fetch_market_data", lambda *args, **kwargs: mock_yfinance_data)
    
    messages = [Message(role="user", content="How is AAPL doing?")]
    response = await portfolio_agent.run(messages)
    
    assert response.agent_name == "portfolio_health"
    content = json.loads(response.content)
    
    assert content["concentration_risk"]["top_position_pct"] == 100.0
    assert content["concentration_risk"]["flag"] == "high"
    assert content["observations"][0] == "Your AAPL holding is doing well."
    assert "performance" in content
    assert "benchmark_comparison" in content
