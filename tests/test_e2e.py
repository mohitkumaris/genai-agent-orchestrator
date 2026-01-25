import pytest
from fastapi.testclient import TestClient
from genai_agent_orchestrator.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "genai-agent-orchestrator"}

@pytest.mark.asyncio
async def test_chat_completions_flow(mock_llm):
    # We need to be careful here. 
    # The Orchestrator calls RouterAgent (LLM call 1) -> Returns "general_agent" (fallback for string mock)
    # Then Orchestrator calls GeneralAgent (LLM call 2).
    
    # Let's configure the mock to return valid JSON for the FIRST call (Router)
    # and simple text for the SECOND call (GeneralAgent).
    # This requires side_effect.
    
    from langchain_core.messages import AIMessage
    
    mock_llm.ainvoke.side_effect = [
        # Call 1: Router
        AIMessage(content='{"destination": "general_agent", "reasoning": "Simple greeting"}'),
        # Call 2: General Agent
        AIMessage(content="Hello! How can I help you?")
    ]

    response = client.post("/v1/chat/completions", json={
        "messages": [{"role": "user", "content": "Hello"}],
        "model": "gpt-4"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["choices"][0]["message"]["content"] == "Hello! How can I help you?"
