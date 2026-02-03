"""
SLA Impact Report

Data structures for simulation output.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class TierImpact:
    """Impact analysis for a specific tier/limit."""
    tier: str
    total_requests: int
    would_warn: int
    would_enforce: int
    avg_cost_saved: float
    avg_score_delta: float  # Placeholder: difficult to estimate without re-running
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
