"""
Outcome Validator

Compares SLA simulation predictions vs actual canary enforcement results.
"""

from typing import List, Dict, Any
from validation.report import DriftReport
from sla.simulator import SLASimulator

class OutcomeValidator:
    """
    Validates simulation accuracy against actual enforcement outcomes.
    """
    
    def __init__(self):
        self._simulator = SLASimulator()
    
    def validate(self, records: List[Dict[str, Any]], tier: str = "free") -> DriftReport:
        """
        Compare simulation predictions vs actual enforcement.
        
        Args:
            records: Evaluation records (from evaluation/reader.py)
            tier: SLA tier to validate
            
        Returns:
            DriftReport with predicted vs actual comparison
        """
        # 1. Filter canary-eligible records
        eligible = self._filter_canary_eligible(records)
        
        if not eligible:
            return DriftReport(
                tier=tier,
                predicted_enforcements=0,
                actual_enforcements=0,
                cost_error_pct=0.0,
                score_error=0.0
            )
        
        # 2. Run simulation on eligible records
        simulation = self._simulator.simulate(eligible, tier)
        predicted = simulation.would_enforce
        
        # 3. Count actual enforcements
        actual = self._count_actual_enforcements(eligible)
        
        # 4. Compute drift
        cost_error_pct = 0.0
        if predicted > 0:
            cost_error_pct = ((predicted - actual) / predicted) * 100
            
        # 5. Score error (placeholder - would need actual vs expected scores)
        score_error = 0.0
        
        return DriftReport(
            tier=tier,
            predicted_enforcements=predicted,
            actual_enforcements=actual,
            cost_error_pct=cost_error_pct,
            score_error=score_error
        )
    
    def _filter_canary_eligible(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter to records that were canary-eligible."""
        eligible = []
        for r in records:
            # Check if record has canary metadata (from routing)
            # Note: We need the full trace metadata, not just evaluation extract
            # For now, we assume all records with policy_status 'warn' were eligible
            if r.get("policy_status") == "warn":
                eligible.append(r)
        return eligible
    
    def _count_actual_enforcements(self, records: List[Dict[str, Any]]) -> int:
        """Count records where enforcement was actually applied."""
        count = 0
        for r in records:
            # In current evaluation/file_store, we don't persist enforcement detail
            # We would need to check if routing_reason indicates enforcement
            # For now, use routing_reason as proxy
            if r.get("routing_reason") and "cost" in str(r.get("routing_reason", "")).lower():
                count += 1
        return count
