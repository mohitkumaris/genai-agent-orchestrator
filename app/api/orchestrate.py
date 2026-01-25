from fastapi import APIRouter, Depends
from schemas.request import ServiceRequest
from schemas.response import ServiceResponse
from orchestration.executor import OrchestrationExecutor
from agents.planner import ExecutionPlan, TaskType

router = APIRouter()
executor = OrchestrationExecutor()

@router.post("/orchestrate", response_model=ServiceResponse)
async def orchestrate(request: ServiceRequest) -> ServiceResponse:
    """
    Entry point for the cognitive engine.
    Wraps the request in a default plan (v1 simplification) and executes.
    """
    # V1: Create a simple plan wrapping the request.
    # In V2: This endpoint would call PlannerAgent first.
    from schemas.plan import PlanStep
    
    # Heuristic: Simple plan
    plan = ExecutionPlan(
        task_type=TaskType.KNOWLEDGE_QUERY,
        rationale="Direct execution via API",
        steps=[
            PlanStep(
                 step_id=1,
                 agent_role="retrieval", # Default to retrieval for knowledge queries
                 intent="answer_user",
                 description="Answer user query",
                 input={"query": request.query}
            )
        ]
    )
    
    result = await executor.execute_plan(plan, request)
    
    return ServiceResponse(
        answer=result.final_output or "No output",
        reasoning=f"Executed Plan {result.plan_id}",
        metadata=result.execution_trace
    )
