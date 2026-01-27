#!/usr/bin/env python3
"""
Pure Python tests for the Critic Agent.

Run: python3 tests/test_critic_pure.py

No external dependencies required beyond the project itself.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from schemas.plan import PlanStep
from schemas.result import CriticResult, RiskLevel, Recommendation, AgentResult
from orchestration.state import StepResult, StepStatus
from genai_mcp_core.context import MCPContext


def create_test_context():
    """Create a minimal MCPContext for testing."""
    return MCPContext.create()


def create_retrieval_result(chunks: list, step_id: int = 1) -> StepResult:
    """Create a mock retrieval step result."""
    return StepResult(
        step_id=step_id,
        agent_role="retrieval",
        status=StepStatus.COMPLETED,
        output={"chunks": chunks},
        metadata={"source": "test", "timestamp": "2026-01-27"},
    )


def create_generation_result(output: str, step_id: int = 2) -> StepResult:
    """Create a mock generation step result."""
    return StepResult(
        step_id=step_id,
        agent_role="general",
        status=StepStatus.COMPLETED,
        output=output,
        metadata={"source": "test", "timestamp": "2026-01-27"},
    )


def test_no_grounding_context():
    """
    Test: No grounding context → HIGH risk, BLOCK
    
    When there are no retrieved chunks, the Critic should:
    - Flag "No grounding context available"
    - Return HIGH risk
    - Recommend BLOCK
    """
    print("=" * 60)
    print("TEST: No grounding context")
    print("=" * 60)
    
    from agents.critic_agent import CriticAgent
    
    agent = CriticAgent()
    ctx = create_test_context()
    step = PlanStep(
        step_id=3,
        agent_role="critic",
        intent="validate_answer",
        description="Ensure the answer is grounded.",
    )
    
    # No retrieval results, only generation
    previous_results = [
        create_generation_result("The capital of France is Paris."),
    ]
    
    result = agent.run(step=step, context=ctx, previous_results=previous_results)
    
    assert isinstance(result, AgentResult), f"Expected AgentResult, got {type(result)}"
    critic_result: CriticResult = result.output
    
    print(f"  is_safe:        {critic_result.is_safe}")
    print(f"  risk_level:     {critic_result.risk_level}")
    print(f"  recommendation: {critic_result.recommendation}")
    print(f"  issues:         {critic_result.issues}")
    
    assert critic_result.is_safe == False, "Should not be safe without grounding"
    assert critic_result.risk_level == RiskLevel.HIGH, f"Expected HIGH risk, got {critic_result.risk_level}"
    assert critic_result.recommendation == Recommendation.BLOCK, f"Expected BLOCK, got {critic_result.recommendation}"
    assert any("grounding" in issue.lower() for issue in critic_result.issues), "Should mention grounding issue"
    
    print("  ✅ PASSED\n")


def test_no_proposed_output():
    """
    Test: No proposed output → HIGH risk, BLOCK
    
    When there is no output to evaluate, the Critic should:
    - Flag "No output to evaluate"
    - Return HIGH risk
    - Recommend BLOCK
    """
    print("=" * 60)
    print("TEST: No proposed output")
    print("=" * 60)
    
    from agents.critic_agent import CriticAgent
    
    agent = CriticAgent()
    ctx = create_test_context()
    step = PlanStep(
        step_id=3,
        agent_role="critic",
        intent="validate_answer",
        description="Ensure the answer is grounded.",
    )
    
    # Only retrieval results, no generation
    previous_results = [
        create_retrieval_result([
            {"text": "Paris is the capital of France."},
            {"text": "France is a country in Western Europe."},
        ]),
    ]
    
    result = agent.run(step=step, context=ctx, previous_results=previous_results)
    critic_result: CriticResult = result.output
    
    print(f"  is_safe:        {critic_result.is_safe}")
    print(f"  risk_level:     {critic_result.risk_level}")
    print(f"  recommendation: {critic_result.recommendation}")
    print(f"  issues:         {critic_result.issues}")
    
    assert critic_result.is_safe == False, "Should not be safe without output"
    assert critic_result.risk_level == RiskLevel.HIGH, f"Expected HIGH risk, got {critic_result.risk_level}"
    assert critic_result.recommendation == Recommendation.BLOCK, f"Expected BLOCK, got {critic_result.recommendation}"
    assert any("output" in issue.lower() for issue in critic_result.issues), "Should mention missing output"
    
    print("  ✅ PASSED\n")


def test_valid_grounded_output():
    """
    Test: Valid grounded output → LOW risk, PROCEED
    
    When output is well-grounded in retrieved context, the Critic should:
    - Return is_safe=True
    - Return LOW or MEDIUM risk
    - Recommend PROCEED or WARN
    """
    print("=" * 60)
    print("TEST: Valid grounded output")
    print("=" * 60)
    
    from agents.critic_agent import CriticAgent
    
    agent = CriticAgent()
    ctx = create_test_context()
    step = PlanStep(
        step_id=3,
        agent_role="critic",
        intent="validate_answer",
        description="Ensure the answer is grounded.",
    )
    
    # Matching content between retrieval and generation
    previous_results = [
        create_retrieval_result([
            {"text": "Paris is the capital city of France.", "source": "wiki", "timestamp": "2026-01-27"},
            {"text": "France is located in Western Europe.", "source": "wiki", "timestamp": "2026-01-27"},
            {"text": "Paris has a population of over 2 million people.", "source": "wiki", "timestamp": "2026-01-27"},
        ]),
        create_generation_result("Paris is the capital of France, located in Western Europe."),
    ]
    
    result = agent.run(step=step, context=ctx, previous_results=previous_results)
    critic_result: CriticResult = result.output
    
    print(f"  is_safe:        {critic_result.is_safe}")
    print(f"  risk_level:     {critic_result.risk_level}")
    print(f"  recommendation: {critic_result.recommendation}")
    print(f"  grounding_score: {critic_result.grounding_score:.2f}")
    print(f"  issues:         {critic_result.issues}")
    
    # With good grounding, we expect low/medium risk
    assert critic_result.grounding_score >= 0.3, f"Expected decent grounding, got {critic_result.grounding_score}"
    assert critic_result.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM), f"Expected LOW/MEDIUM risk, got {critic_result.risk_level}"
    
    print("  ✅ PASSED\n")


def test_weak_grounding():
    """
    Test: Weak grounding → MEDIUM risk, WARN
    
    When output is poorly grounded, the Critic should:
    - Return is_safe=False
    - Return MEDIUM or HIGH risk
    - Recommend WARN or BLOCK
    """
    print("=" * 60)
    print("TEST: Weak grounding")
    print("=" * 60)
    
    from agents.critic_agent import CriticAgent
    
    agent = CriticAgent()
    ctx = create_test_context()
    step = PlanStep(
        step_id=3,
        agent_role="critic",
        intent="validate_answer",
        description="Ensure the answer is grounded.",
    )
    
    # Mismatched content - output talks about something not in context
    previous_results = [
        create_retrieval_result([
            {"text": "The weather in Tokyo is mild.", "source": "weather", "timestamp": "2026-01-27"},
            {"text": "Japan has four distinct seasons.", "source": "wiki", "timestamp": "2026-01-27"},
        ]),
        create_generation_result("Berlin is the capital of Germany and has excellent public transit."),
    ]
    
    result = agent.run(step=step, context=ctx, previous_results=previous_results)
    critic_result: CriticResult = result.output
    
    print(f"  is_safe:        {critic_result.is_safe}")
    print(f"  risk_level:     {critic_result.risk_level}")
    print(f"  recommendation: {critic_result.recommendation}")
    print(f"  grounding_score: {critic_result.grounding_score:.2f}")
    print(f"  issues:         {critic_result.issues}")
    
    # With poor grounding, we expect medium/high risk
    assert critic_result.grounding_score < 0.5, f"Expected weak grounding, got {critic_result.grounding_score}"
    assert critic_result.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH), f"Expected MEDIUM/HIGH risk, got {critic_result.risk_level}"
    assert critic_result.recommendation in (Recommendation.WARN, Recommendation.BLOCK), f"Expected WARN/BLOCK, got {critic_result.recommendation}"
    
    print("  ✅ PASSED\n")


def test_critic_result_schema():
    """
    Test: CriticResult schema is machine-readable and complete.
    """
    print("=" * 60)
    print("TEST: CriticResult schema validation")
    print("=" * 60)
    
    result = CriticResult(
        is_safe=True,
        risk_level=RiskLevel.LOW,
        issues=[],
        recommendation=Recommendation.PROCEED,
        grounding_score=0.8,
        confidence_score=0.9,
    )
    
    # Test serialization
    result_dict = result.model_dump()
    
    print(f"  Serialized keys: {list(result_dict.keys())}")
    
    assert "is_safe" in result_dict
    assert "risk_level" in result_dict
    assert "issues" in result_dict
    assert "recommendation" in result_dict
    assert "validated_claims" in result_dict
    assert "grounding_score" in result_dict
    assert "confidence_score" in result_dict
    
    # Test that enums serialize as strings
    assert result_dict["risk_level"] == "low"
    assert result_dict["recommendation"] == "proceed"
    
    print("  ✅ PASSED\n")


def run_all_tests():
    """Run all Critic Agent tests."""
    print("\n" + "=" * 60)
    print("   CRITIC AGENT TEST SUITE")
    print("=" * 60 + "\n")
    
    tests = [
        test_critic_result_schema,
        test_no_grounding_context,
        test_no_proposed_output,
        test_valid_grounded_output,
        test_weak_grounding,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ FAILED: {e}\n")
            failed += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}\n")
            failed += 1
    
    print("=" * 60)
    print(f"   RESULTS: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
