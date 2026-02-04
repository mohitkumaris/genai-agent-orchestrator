"""
Validation Report

Data structures for outcome validation.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class DriftReport:
    """Comparison of simulated vs actual enforcement."""
    tier: str
    predicted_enforcements: int
    actual_enforcements: int
    cost_error_pct: float
    score_error: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
