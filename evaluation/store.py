"""
Evaluation Store Interface

Abstract interface for persisting evaluation signals.
Storage-agnostic - implementations can write to files, databases, cloud, etc.

DESIGN RULES:
- Post-execution only (observability layer)
- Never affects runtime behavior
- Never throws (graceful failure)
"""

from abc import ABC, abstractmethod
from observability.trace import ExecutionTrace


class EvaluationStore(ABC):
    """
    Abstract base for evaluation persistence.
    
    Implementations:
    - FileEvaluationStore (JSONL, local)
    - DatabaseStore (future)
    - CloudStore (future - BigQuery, etc.)
    """
    
    @abstractmethod
    def save(self, trace: ExecutionTrace) -> None:
        """
        Persist evaluation data from a trace.
        
        Must not throw - failures should be logged and ignored.
        Must not affect request flow.
        
        Args:
            trace: The execution trace containing evaluation metadata
        """
        pass
