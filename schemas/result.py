from typing import Any, Optional
from pydantic import BaseModel, Field

class AgentResult(BaseModel):
    """
    Uniform output structure for all agents.
    """
    agent: str
    output: Any
    metadata: dict = Field(default_factory=dict)
    
    @classmethod
    def success(cls, agent: str, output: Any, metadata: Optional[dict] = None) -> "AgentResult":
        return cls(agent=agent, output=output, metadata=metadata or {})
