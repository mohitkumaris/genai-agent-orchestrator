import asyncio
import sys
import os

# Add root to path
sys.path.append(os.getcwd())

from agents.planner import ExecutionPlan, PlanStep, TaskType
from orchestration.executor import OrchestrationExecutor
from orchestration.state import StepStatus
from schemas.request import ServiceRequest

async def test_executor():
    print("Testing OrchestrationExecutor...")
    
    # 1. Setup Mock Plan
    plan = ExecutionPlan(
        task_type=TaskType.KNOWLEDGE_QUERY,
        rationale="Test Plan",
        steps=[
            PlanStep(
                step_id=1,
                agent_role="general", # Matches GeneralAgent in Executor map
                intent="say_hello",
                description="Say hello"
            ),
            PlanStep(
                step_id=2, 
                agent_role="unknown_agent", # Should Fail
                intent="fail_test", 
                description="Should fail"
            )
        ]
    )
    
    # 2. Setup Context
    req = ServiceRequest(query="Test")
    
    # Mock Agents
    class MockAgent:
        async def execute(self, req):
             from schemas.response import ServiceResponse
             return ServiceResponse(answer="Mock Success")

    # 3. Execute
    executor = OrchestrationExecutor()
    # Replace real agents with mocks
    executor.agents["general"] = MockAgent()
    
    result = await executor.execute_plan(plan, req)
    
    # 4. Verify
    print(f"Plan ID: {result.plan_id}")
    print(f"Global Status: {result.status}")
    
    assert result.status == StepStatus.FAILED, "Global status should be FAILED due to missing agent"
    assert len(result.step_results) == 2, "Should have attempted 2 steps"
    
    # Step 1 Success
    assert result.step_results[0].status == StepStatus.COMPLETED
    print("Step 1: OK")
    
    # Step 2 Failure
    assert result.step_results[1].status == StepStatus.FAILED
    assert "No agent found" in result.step_results[1].error
    print("Step 2: Correctly Failed")
    
    print("PASS: OrchestrationExecutor logic verified.")

if __name__ == "__main__":
    asyncio.run(test_executor())
