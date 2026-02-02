"""
Execution Trace Model

Captures the full lifecycle of a request for observability.
This is a side-effect-only data structure - no business logic.

DESIGN RULES:
- Pure data container
- No dependencies on agents/tools
- Immutable after creation
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ExecutionTrace:
    """
    Immutable trace of a single request execution.
    
    Captures:
    - Identity (request_id, agent_name)
    - Timing (started_at, finished_at, latency_ms)
    - Outcome (success, error)
    - Full metadata tree (routing, RAG, validation, evaluation)
    """
    
    request_id: str
    agent_name: str
    success: bool
    started_at: datetime
    finished_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    @property
    def latency_ms(self) -> int:
        """Calculate latency in milliseconds."""
        delta = self.finished_at - self.started_at
        return int(delta.total_seconds() * 1000)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging/export."""
        return {
            "request_id": self.request_id,
            "agent_name": self.agent_name,
            "success": self.success,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "latency_ms": self.latency_ms,
            "metadata": self.metadata,
            "error": self.error,
        }
