from enum import Enum
import uuid
from typing import List, Optional, Any
from pydantic import BaseModel, Field

# --- Taxonomy ---

class TaskType(str, Enum):
    """
    Explicit classification of the user request.
    """
    KNOWLEDGE_QUERY = "knowledge_query"
    ANALYSIS = "analysis"
    PREDICTION = "prediction"
    MONITORING = "monitoring"
    MIXED = "mixed"

# --- Plan Schemas ---

class PlanStep(BaseModel):
    """
    A single atomic step in the execution plan.
    """
    step_id: int = Field(..., description="1-based step index")
    agent_role: str = Field(..., description="The role of the agent to invoke (e.g., 'retrieval', 'analytics')")
    intent: str = Field(..., description="What this step aims to achieve")
    description: str = Field(..., description="Human-readable description of the step")
    depends_on: List[int] = Field(default_factory=list, description="Step IDs that must complete first")
    input: Optional[Any] = Field(default=None, description="Input payload for the step")

class ExecutionPlan(BaseModel):
    """
    The complete, machine-readable plan of action.
    """
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for this plan")
    task_type: TaskType
    rationale: str = Field(..., description="Brief explaination of why this plan was chosen")
    steps: List[PlanStep] = Field(..., description="Ordered list of steps to execute")
    estimated_complexity: str = Field("unknown", description="Low, Medium, High")
