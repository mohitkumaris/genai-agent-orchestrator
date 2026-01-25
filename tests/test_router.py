import pytest
from unittest.mock import AsyncMock
from genai_agent_orchestrator.agents.router import RouterAgent, RouteDecision
from genai_agent_orchestrator.models.domain import AgentRequest

@pytest.mark.asyncio
async def test_router_routing(mock_llm):
    # Setup mock to return a valid RouteDecision structure (simulated)
    # Since we use a PydanticOutputParser, the LLM usually returns JSON. 
    # But we are mocking the *chain* execution or the LLM response.
    # The simplest is to mock the chain's ainvoke if we could intercept it, 
    # but since it's built inside the method, we rely on mocking the LLM's output 
    # and hoping the parser processes it.
    
    # However, output parsers are fragile with simple string mocks. 
    # Let's bypass the chain logic for unit testing the *surrounding* logic 
    # or craft a JSON string.
    
    mock_llm.ainvoke.return_value.content = '{"destination": "retrieval_agent", "reasoning": "Need to look up docs"}'
    
    agent = RouterAgent()
    request = AgentRequest(query="What is the refund policy?")
    
    result = await agent.run(request)
    
    assert result.answer == "retrieval_agent"
    assert result.reasoning == "Need to look up docs"
