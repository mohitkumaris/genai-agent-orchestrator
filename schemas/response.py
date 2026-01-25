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
