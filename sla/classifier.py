"""
SLA Classifier

Determines the SLA tier for a request.
"""

from typing import Dict, Any, Tuple
from sla.config import TIERS, SLALimits

def classify_request(metadata: Dict[str, Any]) -> Tuple[str, SLALimits]:
    """
    Classify a request into an SLA tier.
    
    Logic:
    - Default to "free"
    - If needed, can inspect metadata (e.g. session_id, user_id)
    - Deterministic and fast
    """
    # Placeholder for future logic (e.g. check header)
    # tier = "premium" if some_condition else "free"
    
    tier = "free"  # Default
    return tier, TIERS[tier]
