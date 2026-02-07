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
from enforcement.audit import EnforcementAudit

if TYPE_CHECKING:
    from evaluation.store import EvaluationStore

# Cost estimation (lazy import to avoid circular deps)
def _estimate_cost(metadata: Dict[str, Any]) -> float:
    """Lazy wrapper for cost estimation."""
    try:
        from cost.estimator import estimate_cost
        return estimate_cost(metadata)
    except Exception:
        return 0.0


# Policy evaluation (lazy import to avoid circular deps)
def _evaluate_policy(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Lazy wrapper for policy evaluation."""
    try:
        from policy.evaluator import evaluate_policy
        result = evaluate_policy(metadata)
        return result.to_dict()
    except Exception:
        return {"status": "error", "violations": [], "warnings": []}



# SLA Classifier (lazy import)
def _classify_sla(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Lazy wrapper for SLA classification."""
    try:
        from sla.classifier import classify_request
        tier, limits = classify_request(metadata)
        return {
            "tier": tier,
            "limits": limits.to_dict()
        }
    except Exception:
        return {"tier": "unknown", "limits": {}}


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
            
            # Compute cost estimate and add to metadata
            metadata_with_cost = dict(result.metadata)
            metadata_with_cost["estimated_cost_usd"] = _estimate_cost(result.metadata)
            
            # Evaluate policy (read-only, no action)
            metadata_with_cost["policy"] = _evaluate_policy(metadata_with_cost)
            
            # Attach SLA (read-only)
            metadata_with_cost["sla"] = _classify_sla(metadata_with_cost)
            
            trace = ExecutionTrace(
                request_id=request_id,
                agent_name=result.agent_name,
                success=success,
                started_at=started_at,
                finished_at=finished_at,
                metadata=metadata_with_cost,
                error=error,
            )
            
            # Emit to console/sink
            self._sink.emit(trace)
            
            # Persist evaluation data (if store configured)
            self._save_evaluation(trace)
            
            # Audit Enforcement
            self._audit_enforcement(trace)
            
            # Publish to LLMOps (fire-and-forget)
            self._publish_to_llmops(trace)
            
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

    def _audit_enforcement(self, trace: ExecutionTrace) -> None:
        """
        Check for and log enforcement actions and canary events for audit.
        """
        routing = trace.metadata.get("routing", {})
        enforcement_data = routing.get("policy_enforcement")
        canary_data = routing.get("canary")
        
        # 1. Standard Enforcement Audit
        if enforcement_data and enforcement_data.get("applied"):
            audit = EnforcementAudit(
                rule_id=enforcement_data["type"],
                action="enforce_routing",
                trigger_reason=enforcement_data["reason"],
                applied=True,
                timestamp=trace.finished_at or datetime.now(),
                request_id=trace.request_id
            )
            # Add canary info if present (via log message)
            extra = f" Canary: {canary_data}" if canary_data else ""
            print(f"[AUDIT] Enforcement applied: {audit.to_dict()}{extra}")
            
        # 2. Canary Skipped (Eligible but not sampled)
        elif canary_data and canary_data.get("eligible") and not canary_data.get("sampled"):
             # Record that it was eligible but skipped due to sampling
             audit = EnforcementAudit(
                rule_id="cost_guard",
                action="canary_skip",
                trigger_reason="sampled_out",
                applied=False,
                timestamp=trace.finished_at or datetime.now(),
                request_id=trace.request_id
             )
             print(f"[AUDIT] Canary Skipped: {audit.to_dict()} Canary: {canary_data}")

    def _publish_to_llmops(self, trace: ExecutionTrace) -> None:
        """
        Publish trace to LLMOps platform.
        
        Fire-and-forget. Never throws. Never blocks execution.
        """
        try:
            from observability.llmops_publisher import publish_all
            publish_all(trace)
        except Exception as e:
            # Never throw - observability failure must not affect execution
            print(f"[LLMOPS] Failed to publish: {e}")
