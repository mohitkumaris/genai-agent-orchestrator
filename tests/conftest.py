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
    # LLMProvider seems to have been removed or refactored.
    # For now, we simply return the mock_llm to satisfy the fixture signature.
    # If specific tests need to patch internal LLM calls (e.g. langchain_adapter), 
    # they should do it in the test itself or we can add it here later.
    return mock_llm
