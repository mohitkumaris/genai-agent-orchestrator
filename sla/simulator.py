"""
SLA Simulator

Offline simulation of SLA enforcement on historical data.
"""

from typing import List, Dict, Any, Optional
from sla.impact_report import TierImpact
from sla.config import TIERS

class SLASimulator:
    """
    Simulates applying SLA limits to past traffic.
    """
    
    def simulate(
        self, 
        records: List[Dict[str, Any]], 
        tier_name: str, 
        custom_limit: Optional[float] = None
    ) -> TierImpact:
        """
        Run simulation for a specific tier.
        
        Args:
            records: List of evaluation records
            tier_name: Name of the tier ("free", "standard", etc.)
            custom_limit: Optional override for max_cost
            
        Returns:
            TierImpact analysis
        """
        limit = custom_limit
        if limit is None and tier_name in TIERS:
            limit = TIERS[tier_name].max_cost
            
        total = len(records)
        would_warn = 0
        would_enforce = 0
        total_savings = 0.0
        
        if limit is None:
            # Unlimited tier
            return TierImpact(
                tier=tier_name,
                total_requests=total,
                would_warn=0,
                would_enforce=0,
                avg_cost_saved=0.0,
                avg_score_delta=0.0
            )
            
        count_for_savings = 0
        
        for r in records:
            cost = r.get("estimated_cost_usd", 0.0)
            policy = r.get("policy_status")  # pass, warn, fail
            
            if cost > limit:
                would_warn += 1
                
                # We enforce if we warn AND policy was already warning/failing
                # (This mimics "Selective Enforcement")
                if policy in ["warn", "fail"]:
                    would_enforce += 1
                    total_savings += (cost - limit)
                    count_for_savings += 1
        
        avg_savings = total_savings / count_for_savings if count_for_savings > 0 else 0.0
        
        return TierImpact(
            tier=tier_name,
            total_requests=total,
            would_warn=would_warn,
            would_enforce=would_enforce,
            avg_cost_saved=avg_savings,
            avg_score_delta=0.0 # Cannot know without re-running
        )
