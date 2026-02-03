"""
Evaluation Reader

Loads evaluation records from JSONL storage for offline analysis.

DESIGN RULES:
- Read-only operations
- No side effects
- Supports filtering
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


def load_records(
    path: str = "evaluations.jsonl",
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Load evaluation records from JSONL file.
    
    Args:
        path: Path to JSONL file
        limit: Maximum number of records to load (None for all)
        
    Returns:
        List of evaluation records
    """
    file_path = Path(path)
    
    if not file_path.exists():
        return []
    
    records = []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
                    
                    if limit and len(records) >= limit:
                        break
                        
    except Exception as e:
        print(f"[READER ERROR] Failed to load records: {e}")
    
    return records


def filter_records(
    records: List[Dict[str, Any]],
    agent_name: Optional[str] = None,
    success_only: bool = False,
    min_score: Optional[float] = None,
    max_cost: Optional[float] = None,
    since: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Filter records by criteria.
    
    Args:
        records: List of evaluation records
        agent_name: Filter by agent name
        success_only: Only include successful requests
        min_score: Minimum evaluation score
        max_cost: Maximum cost
        since: Only records after this datetime
        
    Returns:
        Filtered list of records
    """
    filtered = records
    
    if agent_name:
        filtered = [r for r in filtered if r.get("agent_name") == agent_name]
    
    if success_only:
        filtered = [r for r in filtered if r.get("success") is True]
    
    if min_score is not None:
        filtered = [
            r for r in filtered 
            if r.get("evaluation_score") is not None 
            and r["evaluation_score"] >= min_score
        ]
    
    if max_cost is not None:
        filtered = [
            r for r in filtered 
            if r.get("estimated_cost_usd") is not None 
            and r["estimated_cost_usd"] <= max_cost
        ]
    
    if since:
        filtered = [
            r for r in filtered 
            if r.get("timestamp") 
            and datetime.fromisoformat(r["timestamp"]) >= since
        ]
    
    return filtered


def get_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get summary statistics for records.
    
    Returns:
        Dict with count, avg_score, avg_cost, etc.
    """
    if not records:
        return {"count": 0}
    
    scores = [r["evaluation_score"] for r in records if r.get("evaluation_score") is not None]
    costs = [r["estimated_cost_usd"] for r in records if r.get("estimated_cost_usd") is not None]
    latencies = [r["latency_ms"] for r in records if r.get("latency_ms") is not None]
    
    return {
        "count": len(records),
        "avg_score": sum(scores) / len(scores) if scores else None,
        "avg_cost_usd": sum(costs) / len(costs) if costs else None,
        "total_cost_usd": sum(costs) if costs else 0,
        "avg_latency_ms": sum(latencies) / len(latencies) if latencies else None,
        "success_rate": sum(1 for r in records if r.get("success")) / len(records),
    }
