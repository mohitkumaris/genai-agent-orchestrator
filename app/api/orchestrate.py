"""
Orchestrate API Route

Thin delegation layer to orchestration executor.
Contains NO business logic, routing, or agent-specific code.

DESIGN RULE: This file should never change for LLM, MCP, or RAG work.
All intelligence lives in the orchestration and agent layers.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Dict, Any

from orchestration.executor import OrchestrationExecutor


router = APIRouter()

# Singleton executor instance
_executor = OrchestrationExecutor()


class OrchestrateRequest(BaseModel):
    """API request for orchestration."""
    prompt: str = Field(..., description="User's prompt")


class OrchestrateResult(BaseModel):
    """Structured result from agent execution."""
    agent_name: str = Field(..., description="Name of the agent that handled the request")
    output: str = Field(..., description="The generated response")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata")


class OrchestrateResponse(BaseModel):
    """API response for orchestration."""
    request_id: str = Field(..., description="Request identifier")
    result: OrchestrateResult = Field(..., description="Orchestration result")


@router.post("/orchestrate", response_model=OrchestrateResponse)
def orchestrate(request: OrchestrateRequest) -> OrchestrateResponse:
    """
    Orchestrate a user request.
    
    Flow:
    1. Planner decides which agent to use
    2. Selected agent executes
    3. AgentResult returned with routing metadata
    
    No business logic, routing, or agent selection happens here.
    """
    # Delegate to orchestration layer (planner decides dynamically)
    result, decision = _executor.orchestrate(prompt=request.prompt)
    
    return OrchestrateResponse(
        request_id="wired",
        result=OrchestrateResult(
            agent_name=result.agent_name,
            output=result.output,
            confidence=result.confidence,
            metadata=result.metadata,
        ),
    )
