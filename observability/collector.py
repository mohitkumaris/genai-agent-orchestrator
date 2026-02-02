"""
Trace Collector

Coordinates trace creation and emission.
Single point of trace management for the executor.

DESIGN RULES:
- Never throw exceptions
- Graceful failure handling
- Configurable enable/disable
"""

from datetime import datetime
from typing import Any, Dict, Optional, TYPE_CHECKING

from observability.trace import ExecutionTrace
from observability.sink import TraceSink, ConsoleTraceSink
from schemas.result import AgentResult

if TYPE_CHECKING:
    from evaluation.store import EvaluationStore


class TraceCollector:
    """
    Coordinates trace lifecycle.
    
    Responsibilities:
    - Create traces from execution results
    - Forward to configured sink
    - Persist to evaluation store (optional)
    - Handle failures gracefully (never throw)
    """
    
    def __init__(
        self,
        sink: Optional[TraceSink] = None,
        enabled: bool = True,
        evaluation_store: Optional["EvaluationStore"] = None,
    ):
        """
        Initialize trace collector.
        
        Args:
            sink: TraceSink to emit traces to. Defaults to ConsoleTraceSink.
            enabled: Whether tracing is enabled. Can be toggled at runtime.
            evaluation_store: Optional store for persisting evaluation data.
        """
        self._sink = sink or ConsoleTraceSink()
        self._enabled = enabled
        self._evaluation_store = evaluation_store
    
    @property
    def enabled(self) -> bool:
        """Check if tracing is enabled."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable tracing at runtime."""
        self._enabled = value
    
    def capture(
        self,
        request_id: str,
        result: AgentResult,
        started_at: datetime,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """
        Capture and emit a trace from an execution result.
        
        Args:
            request_id: Unique identifier for this request
            result: The AgentResult from execution
            started_at: When execution started
            success: Whether execution succeeded
            error: Error message if failed
            
        Note: This method NEVER throws. Failures are logged and ignored.
        """
        if not self._enabled:
            return
        
        try:
            finished_at = datetime.now()
            
            trace = ExecutionTrace(
                request_id=request_id,
                agent_name=result.agent_name,
                success=success,
                started_at=started_at,
                finished_at=finished_at,
                metadata=result.metadata,
                error=error,
            )
            
            # Emit to console/sink
            self._sink.emit(trace)
            
            # Persist evaluation data (if store configured)
            self._save_evaluation(trace)
            
        except Exception as e:
            # Never throw - just log the failure
            print(f"[TRACE COLLECTOR ERROR] Failed to capture trace: {e}")
    
    def capture_failure(
        self,
        request_id: str,
        agent_name: str,
        started_at: datetime,
        error: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Capture a trace for a failed execution (before AgentResult exists).
        
        Args:
            request_id: Unique identifier for this request
            agent_name: Agent that was selected/attempted
            started_at: When execution started
            error: Error message
            metadata: Any partial metadata collected
        """
        if not self._enabled:
            return
        
        try:
            finished_at = datetime.now()
            
            trace = ExecutionTrace(
                request_id=request_id,
                agent_name=agent_name,
                success=False,
                started_at=started_at,
                finished_at=finished_at,
                metadata=metadata or {},
                error=error,
            )
            
            # Emit to console/sink
            self._sink.emit(trace)
            
            # Persist evaluation data (if store configured)
            self._save_evaluation(trace)
            
        except Exception as e:
            print(f"[TRACE COLLECTOR ERROR] Failed to capture failure trace: {e}")
    
    def _save_evaluation(self, trace: ExecutionTrace) -> None:
        """
        Save trace to evaluation store if configured.
        
        Never throws - failures are logged and ignored.
        """
        if not self._evaluation_store:
            return
        
        try:
            self._evaluation_store.save(trace)
        except Exception as e:
            print(f"[EVALUATION STORE ERROR] Failed to save evaluation: {e}")

