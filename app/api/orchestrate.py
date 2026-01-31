"""
Orchestrate API Route

TEMPORARY PASS-THROUGH IMPLEMENTATION:
Returns a static JSON response to validate APIM → FastAPI connectivity.
No agent logic, MCP, RAG, or Azure OpenAI invoked.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from schemas.request import OrchestrateRequest


router = APIRouter()


class DebugResult(BaseModel):
    """Debug response result."""
    message: str
    input: str


class DebugResponse(BaseModel):
    """Debug response for APIM → FastAPI validation."""
    request_id: str
    result: DebugResult


@router.post("/orchestrate", response_model=DebugResponse)
def orchestrate(request: OrchestrateRequest) -> DebugResponse:
    """
    Pass-through endpoint for APIM → FastAPI connectivity validation.
    
    Returns a static JSON echoing the input query.
    No async, no dependencies, no orchestration logic.
    """
    return DebugResponse(
        request_id="debug",
        result=DebugResult(
            message="APIM → FastAPI works",
            input=request.query,
        )
    )
