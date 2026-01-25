from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

# Ensure we can reference the plan (conceptual dependency, avoiding circular import if possible)
# In a real app, schemas might be in a shared module. 
# For now, we define Output/State models here.

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class StepResult(BaseModel):
    """
    Result of a single atomic processing step.
    """
    step_id: int
    agent_role: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExecutionResult(BaseModel):
    """
    Final output of the execution run.
    """
    plan_id: str = Field(default_factory=lambda: "unknown")
    status: StepStatus
    step_results: List[StepResult] = Field(default_factory=list)
    final_output: Optional[str] = None
    execution_trace: Dict[str, Any] = Field(default_factory=dict)

class ExecutionState(BaseModel):
    """
    Mutable state tracking during execution (internal use).
    """
    plan_id: str
    current_step_index: int = 0
    results: List[StepResult] = Field(default_factory=list)
    memory: Dict[str, Any] = Field(default_factory=dict)
