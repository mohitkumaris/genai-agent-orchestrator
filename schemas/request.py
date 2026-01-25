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
