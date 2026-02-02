"""
File-based Evaluation Store

JSONL file-based storage for evaluation signals.
Human-readable, easy to inspect, no external dependencies.

DESIGN RULES:
- Append-only (JSONL format)
- Never throws (graceful failure)
- Human-readable output
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from evaluation.store import EvaluationStore
from observability.trace import ExecutionTrace


class FileEvaluationStore(EvaluationStore):
    """
    JSONL file-based evaluation storage.
    
    Each line is a JSON record with:
    - request_id
    - agent_name
    - timestamp
    - latency_ms
    - model
    - evaluation_score
    - validation_valid
    - success
    """
    
    DEFAULT_PATH = "evaluations.jsonl"
    
    def __init__(self, path: str | None = None):
        """
        Initialize file store.
        
        Args:
            path: Path to JSONL file. Defaults to 'evaluations.jsonl' in cwd.
        """
        self._path = Path(path or self.DEFAULT_PATH)
        
        # Ensure parent directory exists
        self._path.parent.mkdir(parents=True, exist_ok=True)
    
    def save(self, trace: ExecutionTrace) -> None:
        """
        Append evaluation record to JSONL file.
        
        Never throws - failures are logged and ignored.
        """
        try:
            record = self._extract_record(trace)
            
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=self._json_serializer) + "\n")
                
        except Exception as e:
            # Never throw - just log failure
            print(f"[EVALUATION STORE ERROR] Failed to save: {e}")
    
    def _extract_record(self, trace: ExecutionTrace) -> dict:
        """Extract relevant fields from trace for storage."""
        metadata = trace.metadata
        
        # Extract evaluation score
        evaluation = metadata.get("evaluation", {})
        evaluation_score = evaluation.get("score") if isinstance(evaluation, dict) else None
        
        # Extract validation result
        validation = metadata.get("validation", {})
        validation_valid = validation.get("is_valid") if isinstance(validation, dict) else None
        
        # Extract model info
        model = metadata.get("model", "unknown")
        
        # Extract routing info
        routing = metadata.get("routing", {})
        routing_reason = routing.get("reason") if isinstance(routing, dict) else None
        
        return {
            "request_id": trace.request_id,
            "agent_name": trace.agent_name,
            "timestamp": trace.started_at.isoformat(),
            "latency_ms": trace.latency_ms,
            "model": model,
            "evaluation_score": evaluation_score,
            "validation_valid": validation_valid,
            "success": trace.success,
            "routing_reason": routing_reason,
            "error": trace.error,
        }
    
    def _json_serializer(self, obj: Any) -> str:
        """Custom JSON serializer for special types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)
    
    def read_all(self) -> list[dict]:
        """
        Read all records from the file (for analysis).
        
        Returns:
            List of evaluation records
        """
        records = []
        
        if not self._path.exists():
            return records
        
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
        except Exception as e:
            print(f"[EVALUATION STORE ERROR] Failed to read: {e}")
        
        return records
    
    def get_statistics(self) -> dict:
        """
        Compute basic statistics from stored evaluations.
        
        Returns:
            Dict with count, avg_score, avg_latency, success_rate
        """
        records = self.read_all()
        
        if not records:
            return {"count": 0}
        
        scores = [r["evaluation_score"] for r in records if r.get("evaluation_score") is not None]
        latencies = [r["latency_ms"] for r in records if r.get("latency_ms") is not None]
        successes = [r["success"] for r in records if r.get("success") is not None]
        
        return {
            "count": len(records),
            "avg_evaluation_score": sum(scores) / len(scores) if scores else None,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else None,
            "success_rate": sum(1 for s in successes if s) / len(successes) if successes else None,
        }
