import json
import pytest
from src.services.intent_classifier import IntentClassifier
from src.schemas.chat import Message, IntentType

def normalize_entities(entities: list[str]) -> set[str]:
    """Normalizes entities by converting to uppercase and stripping whitespace."""
    return {e.strip().upper() for e in entities}

def assert_entities_subset(expected: list[str], actual: list[str]):
    """Asserts that the expected entities are a subset of the actual extracted entities."""
    norm_expected = normalize_entities(expected)
    norm_actual = normalize_entities(actual)
    assert norm_expected.issubset(norm_actual), f"Expected {norm_expected} to be a subset of {norm_actual}"

@pytest.fixture
def classifier(mock_llm):
    return IntentClassifier(llm_client=mock_llm)

@pytest.mark.asyncio
async def test_classify_portfolio_health(classifier: IntentClassifier, mock_llm):
    mock_response = {
        "intent": "portfolio_health",
        "agent": "portfolio_health_agent",
        "entities": {
            "tickers": ["AAPL", "MSFT"],
            "amounts": [],
            "time_periods": []
        },
        "safety": "safe"
    }
    mock_llm.set_response(json.dumps(mock_response))
    
    messages = [Message(role="user", content="How is my portfolio doing? I have AAPL and MSFT.")]
    result = await classifier.classify(messages)
    
    assert result.intent == IntentType.PORTFOLIO_HEALTH
    assert result.agent == "portfolio_health_agent"
    assert_entities_subset(["aapl", "msft"], result.entities.tickers)

@pytest.mark.asyncio
async def test_classify_market_research(classifier: IntentClassifier, mock_llm):
    mock_response = {
        "intent": "market_research",
        "agent": "market_research_agent",
        "entities": {
            "tickers": ["TSLA"],
            "amounts": ["$10,000"],
            "time_periods": []
        },
        "safety": "safe"
    }
    mock_llm.set_response("```json\n" + json.dumps(mock_response) + "\n```")
    
    messages = [Message(role="user", content="Should I invest $10,000 in Tesla?")]
    result = await classifier.classify(messages)
    
    assert result.intent == IntentType.MARKET_RESEARCH
    assert result.agent == "market_research_agent"
    assert_entities_subset(["TSLA"], result.entities.tickers)
    assert_entities_subset(["$10,000"], result.entities.amounts)

@pytest.mark.asyncio
async def test_classify_fallback(classifier: IntentClassifier, mock_llm):
    # Test fallback behavior when JSON parsing fails
    mock_llm.set_response("I am just an AI and I cannot output JSON right now.")
    
    messages = [Message(role="user", content="Hello!")]
    result = await classifier.classify(messages)
    
    assert result.intent == IntentType.UNKNOWN
    assert result.agent == "stub_agent"
