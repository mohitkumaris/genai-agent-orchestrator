import pytest
from unittest.mock import MagicMock, AsyncMock
from langchain_core.messages import AIMessage

@pytest.fixture
def mock_llm():
    mock = MagicMock()
    # Mock ainvoke for chat model
    mock.ainvoke = AsyncMock(return_value=AIMessage(content="Mocked Response"))
    return mock

@pytest.fixture(autouse=True)
def mock_llm_provider(monkeypatch, mock_llm):
    # Patch the LLMProvider to return our mock
    from genai_agent_orchestrator.integration.llm import LLMProvider
    monkeypatch.setattr(LLMProvider, "get_chat_model", lambda **kwargs: mock_llm)
    return mock_llm
