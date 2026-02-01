from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field


# --- Critic Agent Schemas ---

class RiskLevel(str, Enum):
    """Risk classification for validated outputs."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Recommendation(str, Enum):
    """Action recommendation from the Critic Agent."""
    PROCEED = "proceed"
    WARN = "warn"
    BLOCK = "block"


class ValidatedClaim(BaseModel):
    """A single claim extracted and validated against grounding context."""
    claim_text: str
    is_grounded: bool
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    supporting_chunk_ids: List[str] = Field(default_factory=list)


class CriticResult(BaseModel):
    """
    Structured validation output from the Critic Agent.
    
    This is the ONLY output format the Critic produces.
    No prose, no commentary — just structured data.
    """
    is_safe: bool = Field(..., description="Overall safety verdict")
    risk_level: RiskLevel = Field(..., description="Risk classification: low, medium, high")
    issues: List[str] = Field(default_factory=list, description="List of identified issues")
    recommendation: Recommendation = Field(..., description="Action recommendation: proceed, warn, block")
    validated_claims: List[ValidatedClaim] = Field(default_factory=list, description="Claims with grounding status")
    grounding_score: float = Field(default=0.0, ge=0.0, le=1.0, description="How well output aligns with context")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Model confidence in validation")


# --- Agent Result Schema ---

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


class OrchestrationResult(BaseModel):
    """
    Typed result from orchestration layer.
    
    This is the canonical output format for agent execution,
    providing a consistent contract for all agent invocations.
    """
    agent_name: str = Field(..., description="Name of the agent that produced this result")
    output: str = Field(..., description="The agent's output")
