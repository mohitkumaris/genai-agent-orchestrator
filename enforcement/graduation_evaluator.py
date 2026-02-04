"""
Graduation Evaluator

Evaluates enforcement readiness for scale-up.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from enum import Enum

from enforcement.graduation_rules import GraduationThresholds, DEFAULT_THRESHOLDS
from validation.report import DriftReport


class Recommendation(Enum):
    GRADUATE = "GRADUATE"
    HOLD = "HOLD"
    ROLLBACK = "ROLLBACK"


@dataclass
class GraduationResult:
    """Result of graduation evaluation."""
    rule: str
    tier: str
    recommendation: str
    reasons: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GraduationEvaluator:
    """
    Evaluates whether enforcement can be scaled up.
    """
    
    def __init__(self, thresholds: Optional[GraduationThresholds] = None):
        self._thresholds = thresholds or DEFAULT_THRESHOLDS
    
    def evaluate(
        self,
        drift_report: DriftReport,
        audit_records: Optional[List[Dict[str, Any]]] = None,
    ) -> GraduationResult:
        """
        Evaluate graduation readiness.
        
        Args:
            drift_report: Output from OutcomeValidator
            audit_records: Optional list of audit records
            
        Returns:
            GraduationResult with recommendation
        """
        reasons = []
        
        # 1. Check drift
        if abs(drift_report.cost_error_pct) > self._thresholds.max_drift_pct:
            reasons.append(f"drift_exceeded ({drift_report.cost_error_pct:.1f}% > {self._thresholds.max_drift_pct}%)")
        
        # 2. Check score delta
        if abs(drift_report.score_error) > self._thresholds.max_score_delta:
            reasons.append(f"score_delta_exceeded ({drift_report.score_error:.3f} > {self._thresholds.max_score_delta})")
        
        # 3. Check critical audits
        critical_count = 0
        if audit_records:
            for audit in audit_records:
                if audit.get("action") == "rollback" or audit.get("trigger_reason") == "critical":
                    critical_count += 1
        
        if critical_count > self._thresholds.max_critical_audits:
            reasons.append(f"critical_audits ({critical_count} > {self._thresholds.max_critical_audits})")
        
        # Decide recommendation
        if len(reasons) == 0:
            recommendation = Recommendation.GRADUATE
        elif len(reasons) >= 2:
            recommendation = Recommendation.ROLLBACK
        else:
            recommendation = Recommendation.HOLD
        
        return GraduationResult(
            rule="cost_guard",
            tier=drift_report.tier,
            recommendation=recommendation.value,
            reasons=reasons,
        )
