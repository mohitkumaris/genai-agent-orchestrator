from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ServiceResponse(BaseModel):
    """
    Internal response model for the orchestration layer.
    """
    answer: str
    reasoning: Optional[str] = None
    tool_usage: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OrchestrateResponse(BaseModel):
    """
    API response model for the /orchestrate endpoint.
    
    This is the external contract — clients receive this.
    Wraps the essential fields from FinalResponse.
    """
    output: str = Field(..., description="Final response text")
    is_safe: bool = Field(..., description="Whether the response passed validation")
    risk_level: str = Field(..., description="Risk classification: low, medium, high")
    recommendation: str = Field(..., description="Critic recommendation: proceed, warn, block")
    issues: List[str] = Field(default_factory=list, description="List of identified issues")
    trace_id: str = Field(..., description="Trace ID for observability")
    
    @classmethod
    def from_final_response(cls, final: "FinalResponse") -> "OrchestrateResponse":
        """Convert internal FinalResponse to API response."""
        return cls(
            output=final.response_text,
            is_safe=final.is_safe,
            risk_level=final.risk_level,
            recommendation=final.recommendation,
            issues=final.issues,
            trace_id=final.trace_id,
        )


class FinalResponse(BaseModel):
    """
    Complete, machine-readable response from the orchestration flow.
    
    This is the ONLY output format returned to the API Gateway.
    No free-form text blobs — structured data only.
    """
    
    # --- Payload ---
    response_text: str = Field(..., description="Final response text for the user")
    
    # --- Risk/Confidence from Critic ---
    is_safe: bool = Field(..., description="Whether the response passed validation")
    risk_level: str = Field(..., description="Risk classification: low, medium, high")
    recommendation: str = Field(..., description="Critic recommendation: proceed, warn, block")
    issues: List[str] = Field(default_factory=list, description="List of identified issues")
    grounding_score: float = Field(default=0.0, description="How well response aligns with context")
    
    # --- Execution Metadata ---
    plan_id: str = Field(..., description="Unique ID of the executed plan")
    execution_status: str = Field(..., description="Final execution status")
    steps_executed: int = Field(default=0, description="Number of steps executed")
    
    # --- Trace Reference for LLMOps ---
    trace_id: str = Field(..., description="Unique trace ID for observability")
    
    @classmethod
    def from_execution(
        cls,
        execution_result: "ExecutionResult",  # Forward reference
        critic_result: "CriticResult",  # Forward reference
        trace_id: str,
    ) -> "FinalResponse":
        """
        Factory method to assemble FinalResponse from execution and critic results.
        
        Args:
            execution_result: Result from OrchestrationExecutor
            critic_result: Validation result from CriticAgent
            trace_id: Trace ID for observability
            
        Returns:
            FinalResponse: Structured response for API Gateway
        """
        return cls(
            response_text=execution_result.final_output or "No response generated.",
            is_safe=critic_result.is_safe,
            risk_level=critic_result.risk_level.value if hasattr(critic_result.risk_level, 'value') else str(critic_result.risk_level),
            recommendation=critic_result.recommendation.value if hasattr(critic_result.recommendation, 'value') else str(critic_result.recommendation),
            issues=critic_result.issues,
            grounding_score=critic_result.grounding_score,
            plan_id=execution_result.plan_id,
            execution_status=execution_result.status.value if hasattr(execution_result.status, 'value') else str(execution_result.status),
            steps_executed=len(execution_result.step_results),
            trace_id=trace_id,
        )


# Import hints for type checking (avoid circular imports at runtime)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from orchestration.state import ExecutionResult
    from schemas.result import CriticResult
