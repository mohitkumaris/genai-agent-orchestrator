import asyncio
import sys
import os

# Add root to path
sys.path.append(os.getcwd())

from schemas.plan import ExecutionPlan, PlanStep, TaskType
from schemas.request import ServiceRequest
from orchestration.executor import OrchestrationExecutor
from agents.retrieval_agent import RetrievalAgent
from genai_mcp_core.context import MCPContext

async def test_retrieval_flow():
    print("Testing Retrieval Agent and Schema Refactor...")
    
    # 1. Test Schema Instantiation
    print("1. Schema Check")
    plan = ExecutionPlan(
        task_type=TaskType.KNOWLEDGE_QUERY,
        rationale="Schema Test",
        steps=[PlanStep(step_id=1, agent_role="retrieval", intent="test", description="desc", input={"query": "foo"})]
    )
    assert plan.plan_id is not None
    print("Schema OK.")
    
    # 2. Test Retrieval Agent Direct Run
    print("2. Retrieval Agent Direct Run")
    agent = RetrievalAgent()
    ctx = MCPContext.create()
    step = plan.steps[0]
    
    res = agent.run(step=step, context=ctx)
    print(f"Direct Run Output: {res}")
    assert res.agent == "retrieval"
    assert "Mock retrieved content" in str(res.output)
    print("Direct Run OK.")
    
    # 3. Test Orchestrator Bridge
    print("3. Orchestrator Bridge")
    ex = OrchestrationExecutor()
    # Note: Executor uses its internal mapping. We need to make sure it loads the NEW RetrievalAgent.
    # Since we overwrote the file, it should import the new class.
    # However, we mocked it in previous tests. Let's rely on standard import.
    
    req = ServiceRequest(query="bar")
    exec_res = await ex.execute_plan(plan, req)
    
    print(f"Executor Status: {exec_res.status}")
    print(f"Final Output: {exec_res.final_output}")
    
    assert exec_res.status == "completed"
    assert "Mock retrieved content" in exec_res.final_output
    print("Bridge OK.")

if __name__ == "__main__":
    asyncio.run(test_retrieval_flow())
