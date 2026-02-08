import pytest
from unittest.mock import MagicMock, patch
from agents.planner_agent import PlannerAgent, PlannerDecision
from orchestration.planner import OrchestrationPlanner, EnrichedRoutingDecision

def test_planner_determinism():
    """Test that the planner is deterministic for the same input."""
    agent = PlannerAgent()
    query = "What is 2 + 2?"
    decision1 = agent.plan(query)
    decision2 = agent.plan(query)
    
    assert decision1 == decision2
    assert decision1.selected_agent == "general"

def test_planner_trivial_queries():
    """Test routing for trivial queries."""
    agent = PlannerAgent()
    trivial_queries = [
        "What is 2 + 2?",
        "Explain Python lists",
        "Hello",
        "Hi there",
        "",
        "   "
    ]
    
    for query in trivial_queries:
        decision = agent.plan(query)
        assert decision.selected_agent == "general", f"Failed for query: '{query}'"
        assert decision.reason == "Default routing for general queries", f"Wrong reason for query: '{query}'"

def test_planner_retrieval_keywords():
    """Test routing for retrieval keywords."""
    agent = PlannerAgent()
    query = "find the document about policy"
    decision = agent.plan(query)
    assert decision.selected_agent == "retrieval"

def test_planner_critic_keywords():
    """Test routing for validation keywords."""
    agent = PlannerAgent()
    query = "validate this output"
    decision = agent.plan(query)
    assert decision.selected_agent == "critic"

def test_planner_robustness_none_input():
    """Test planner robustness against None input."""
    agent = PlannerAgent()
    # Depending on implementation, this might raise or return default. 
    # The requirement is "Planner must never throw".
    # So we expect this to return default general agent.
    try:
        decision = agent.plan(None)
        assert decision.selected_agent == "general"
    except Exception as e:
        pytest.fail(f"Planner raised exception on None input: {e}")

def test_planner_internal_error_recovery():
    """Test that planner recovers from internal errors."""
    agent = PlannerAgent()
    
    class EvilPrompt:
        def lower(self):
            raise ValueError("Simulated internal error")
        def __contains__(self, item):
            return False
            
    try:
        # Pass an object that raises when lower() is called
        decision = agent.plan(EvilPrompt())  # type: ignore
        assert decision.selected_agent == "general"
        assert decision.reason == "Default routing for general queries"
    except Exception as e:
        pytest.fail(f"Planner failed to recover from internal error: {e}")

def test_orchestration_planner_robustness():
    """Test OrchestrationPlanner robustness."""
    orchestrator = OrchestrationPlanner()
    
    # Test with None prompt
    try:
        decision = orchestrator.plan(None)
        assert decision.selected_agent == "general"
    except Exception as e:
        pytest.fail(f"OrchestrationPlanner raised exception on None prompt: {e}")

    # Test with internal planner failure
    with patch.object(PlannerAgent, 'plan', side_effect=RuntimeError("Agent failure")):
        try:
            decision = orchestrator.plan("test")
            assert decision.selected_agent == "general"
        except Exception as e:
            pytest.fail(f"OrchestrationPlanner failed to recover from agent failure: {e}")
