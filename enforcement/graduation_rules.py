"""
Graduation Rules

Configurable thresholds for enforcement graduation.
"""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class GraduationThresholds:
    """Thresholds for graduation decisions."""
    max_drift_pct: float = 10.0
    min_success_rate: float = 0.99
    max_score_delta: float = 0.05
    max_critical_audits: int = 0


# Default thresholds
DEFAULT_THRESHOLDS = GraduationThresholds()
