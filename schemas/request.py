from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ServiceRequest(BaseModel):
    """
    Internal request model for the orchestration layer.
    """
    query: str
    context: Dict[str, Any] = Field(default_factory=dict)
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    trace_id: Optional[str] = None


class OrchestrateRequest(BaseModel):
    """
    API request model for the /orchestrate endpoint.
    
    This is the external contract — clients send this.
    """
    query: str = Field(..., description="User's query or request")
    user_id: Optional[str] = Field(default=None, description="Optional user identifier")
    session_id: Optional[str] = Field(default=None, description="Optional session identifier")
    
    def to_service_request(self, trace_id: Optional[str] = None) -> ServiceRequest:
        """Convert to internal ServiceRequest."""
        return ServiceRequest(
            query=self.query,
            context={
                "user_id": self.user_id,
                "session_id": self.session_id,
            },
            trace_id=trace_id,
        )
