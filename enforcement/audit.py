"""
Enforcement Audit

Data structures for auditing enforcement decisions.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass
class EnforcementAudit:
    """
    Record of an enforcement decision.
    """
    rule_id: str
    action: str
    trigger_reason: str
    applied: bool
    timestamp: datetime
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data
