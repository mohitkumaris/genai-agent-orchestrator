#!/usr/bin/env python3
"""
End-to-End Flow Tests

Tests the complete orchestration flow:
Request → Planner → Executor → Critic → FinalResponse

Run: python3 tests/test_e2e_flow.py
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from schemas.request import ServiceRequest
from schemas.response import FinalResponse
from orchestration.router import OrchestrationRouter
from orchestration.state import ExecutionResult, StepResult, StepStatus
from schemas.result import CriticResult, RiskLevel, Recommendation


def test_final_response_schema():
    """
    Test: FinalResponse schema serializes correctly.
    """
    print("=" * 60)
    print("TEST: FinalResponse schema validation")
    print("=" * 60)
    
    # Create mock execution result
    execution_result = ExecutionResult(
        plan_id="test-plan-123",
        status=StepStatus.COMPLETED,
        step_results=[
            StepResult(
                step_id=1,
                agent_role="retrieval",
                status=StepStatus.COMPLETED,
                output={"chunks": [{"text": "Paris is the capital of France."}]},
                metadata={"source": "wiki", "timestamp": "2026-01-27"},
            ),
        ],
        final_output="Paris is the capital of France.",
    )
    
    # Create mock critic result
    critic_result = CriticResult(
        is_safe=True,
        risk_level=RiskLevel.LOW,
        issues=[],
        recommendation=Recommendation.PROCEED,
        grounding_score=0.85,
        confidence_score=0.9,
    )
    
    # Assemble FinalResponse
    final_response = FinalResponse.from_execution(
        execution_result=execution_result,
        critic_result=critic_result,
        trace_id="test-trace-456",
    )
    
    print(f"  response_text: {final_response.response_text[:50]}...")
    print(f"  is_safe: {final_response.is_safe}")
    print(f"  risk_level: {final_response.risk_level}")
    print(f"  recommendation: {final_response.recommendation}")
    print(f"  plan_id: {final_response.plan_id}")
    print(f"  trace_id: {final_response.trace_id}")
    
    # Verify serialization
    response_dict = final_response.model_dump()
    
    assert response_dict["is_safe"] == True
    assert response_dict["risk_level"] == "low"
    assert response_dict["recommendation"] == "proceed"
    assert response_dict["plan_id"] == "test-plan-123"
    assert response_dict["trace_id"] == "test-trace-456"
    
    print("  ✅ PASSED\n")


def test_critic_validate_from_execution():
    """
    Test: CriticAgent.validate_from_execution works correctly.
    """
    print("=" * 60)
    print("TEST: Critic validate_from_execution")
    print("=" * 60)
    
    from agents.critic_agent import CriticAgent
    
    critic = CriticAgent()
    
    # Create execution result with grounded output
    execution_result = ExecutionResult(
        plan_id="test-plan-789",
        status=StepStatus.COMPLETED,
        step_results=[
            StepResult(
                step_id=1,
                agent_role="retrieval",
                status=StepStatus.COMPLETED,
                output={"chunks": [
                    {"text": "Paris is the capital city of France."},
                    {"text": "France is located in Western Europe."},
                ]},
                metadata={"source": "wiki", "timestamp": "2026-01-27"},
            ),
            StepResult(
                step_id=2,
                agent_role="general",
                status=StepStatus.COMPLETED,
                output="Paris is the capital of France, located in Western Europe.",
                metadata={},
            ),
        ],
        final_output="Paris is the capital of France, located in Western Europe.",
    )
    
    # Validate
    critic_result = critic.validate_from_execution(execution_result)
    
    print(f"  is_safe: {critic_result.is_safe}")
    print(f"  risk_level: {critic_result.risk_level}")
    print(f"  recommendation: {critic_result.recommendation}")
    print(f"  grounding_score: {critic_result.grounding_score:.2f}")
    print(f"  issues: {critic_result.issues}")
    
    assert critic_result.grounding_score >= 0.3, f"Expected decent grounding, got {critic_result.grounding_score}"
    
    print("  ✅ PASSED\n")


def test_critic_validates_failed_execution():
    """
    Test: Critic correctly handles failed execution.
    """
    print("=" * 60)
    print("TEST: Critic validates failed execution")
    print("=" * 60)
    
    from agents.critic_agent import CriticAgent
    
    critic = CriticAgent()
    
    # Create FAILED execution result
    execution_result = ExecutionResult(
        plan_id="test-plan-failed",
        status=StepStatus.FAILED,
        step_results=[
            StepResult(
                step_id=1,
                agent_role="retrieval",
                status=StepStatus.FAILED,
                error="Connection timeout",
                metadata={},
            ),
        ],
        final_output=None,
    )
    
    # Validate
    critic_result = critic.validate_from_execution(execution_result)
    
    print(f"  is_safe: {critic_result.is_safe}")
    print(f"  risk_level: {critic_result.risk_level}")
    print(f"  recommendation: {critic_result.recommendation}")
    print(f"  issues: {critic_result.issues}")
    
    assert critic_result.is_safe == False, "Failed execution should not be safe"
    assert critic_result.recommendation == Recommendation.BLOCK, f"Expected BLOCK, got {critic_result.recommendation}"
    assert "Execution failed" in critic_result.issues, "Should flag execution failure"
    
    print("  ✅ PASSED\n")


async def test_orchestration_router_flow():
    """
    Test: OrchestrationRouter executes the complete flow.
    """
    print("=" * 60)
    print("TEST: OrchestrationRouter complete flow")
    print("=" * 60)
    
    router = OrchestrationRouter()
    
    request = ServiceRequest(
        query="What is the capital of France?",
        context={},
        trace_id="e2e-test-001",
    )
    
    # Execute the full flow
    final_response = await router.handle(request=request)
    
    print(f"  response_text: {final_response.response_text[:60]}...")
    print(f"  is_safe: {final_response.is_safe}")
    print(f"  risk_level: {final_response.risk_level}")
    print(f"  recommendation: {final_response.recommendation}")
    print(f"  plan_id: {final_response.plan_id}")
    print(f"  steps_executed: {final_response.steps_executed}")
    print(f"  trace_id: {final_response.trace_id}")
    
    # Verify structure
    assert isinstance(final_response, FinalResponse)
    assert final_response.trace_id == "e2e-test-001"
    assert final_response.steps_executed > 0
    
    print("  ✅ PASSED\n")


def test_flow_guarantees():
    """
    Test: Verify single-direction flow guarantees.
    """
    print("=" * 60)
    print("TEST: Flow guarantees (structural)")
    print("=" * 60)
    
    # 1. Verify OrchestrationRouter has correct dependencies
    from orchestration.router import OrchestrationRouter
    from agents.planner import PlannerAgent
    from agents.critic_agent import CriticAgent
    from orchestration.executor import OrchestrationExecutor
    
    router = OrchestrationRouter()
    
    assert isinstance(router._planner, PlannerAgent), "Router must have PlannerAgent"
    assert isinstance(router._executor, OrchestrationExecutor), "Router must have Executor"
    assert isinstance(router._critic, CriticAgent), "Router must have CriticAgent"
    
    print("  ✓ Router has correct dependencies")
    
    # 2. Verify FinalResponse has required fields
    from schemas.response import FinalResponse
    
    fields = FinalResponse.model_fields
    required_fields = ["response_text", "is_safe", "risk_level", "recommendation", "plan_id", "trace_id"]
    
    for field in required_fields:
        assert field in fields, f"FinalResponse missing required field: {field}"
    
    print("  ✓ FinalResponse has required fields")
    
    # 3. Verify CriticAgent has validate_from_execution
    from agents.critic_agent import CriticAgent
    
    critic = CriticAgent()
    assert hasattr(critic, "validate_from_execution"), "CriticAgent must have validate_from_execution"
    
    print("  ✓ CriticAgent has validate_from_execution")
    
    print("  ✅ PASSED\n")


def run_all_tests():
    """Run all end-to-end flow tests."""
    print("\n" + "=" * 60)
    print("   END-TO-END FLOW TEST SUITE")
    print("=" * 60 + "\n")
    
    sync_tests = [
        test_final_response_schema,
        test_critic_validate_from_execution,
        test_critic_validates_failed_execution,
        test_flow_guarantees,
    ]
    
    async_tests = [
        test_orchestration_router_flow,
    ]
    
    passed = 0
    failed = 0
    
    # Run sync tests
    for test in sync_tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ FAILED: {e}\n")
            failed += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}\n")
            failed += 1
    
    # Run async tests
    for test in async_tests:
        try:
            asyncio.run(test())
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
