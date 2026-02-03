"""
SLA Configuration

Tier definitions and limits.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

@dataclass
class SLALimits:
    """Limits associated with an SLA tier."""
    max_cost: Optional[float]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# Tier Definitions
TIERS: Dict[str, SLALimits] = {
    "free": SLALimits(max_cost=0.00005),
    "standard": SLALimits(max_cost=0.0002),
    "premium": SLALimits(max_cost=None),
}
