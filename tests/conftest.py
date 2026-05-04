import pytest
from src.llm.client import BaseLLMClient
from src.schemas.chat import Message
from typing import AsyncIterator

class MockLLMClient(BaseLLMClient):
    def __init__(self):
        self.responses = []
        self.stream_responses = []

    def set_response(self, response: str):
        self.responses.append(response)
        
    def set_stream_response(self, tokens: list[str]):
        self.stream_responses.append(tokens)

    async def complete(self, messages: list[Message], **kwargs) -> str:
        if self.responses:
            return self.responses.pop(0)
        return ""

    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        if self.stream_responses:
            tokens = self.stream_responses.pop(0)
            for token in tokens:
                yield token
        else:
            yield ""

@pytest.fixture
def mock_llm():
    return MockLLMClient()
