"""
Enforcement Configuration

Centralized control for policy enforcement.
Provides global kill switch and rule-level toggles.
"""

import os
from typing import Set

class EnforcementConfig:
    """
    Global configuration for enforcement.
    
    Attributes:
        ENFORCEMENT_ENABLED: Master kill switch. If False, NO enforcement runs.
        ENABLED_RULES: Set of active rule IDs.
    """
    
    # Global Master Kill Switch
    # Defaults to True, but can be disabled via env var for emergency
    ENFORCEMENT_ENABLED: bool = os.getenv("GENAI_ENFORCEMENT_ENABLED", "true").lower() == "true"
    
    # Active Rules Registry
    ENABLED_RULES: Set[str] = {
        "cost_guard",
        # Future: "safety_guard", "compliance_guard"
    }
    
    # Canary Configuration
    CANARY_ENFORCEMENT: dict = {
        "enabled": True,
        "tier": "free",
        "percentage": 5  # 5% rollout
    }
    
    @classmethod
    def is_enabled(cls, rule_id: str) -> bool:
        """
        Check if a specific rule should be enforced.
        
        Args:
            rule_id: The ID of the enforcement rule (e.g., "cost_guard")
            
        Returns:
            True only if Global Switch is ON and rule is in ENABLED_RULES.
        """
        if not cls.ENFORCEMENT_ENABLED:
            return False
            
        return rule_id in cls.ENABLED_RULES
    
    @classmethod
    def is_globally_disabled(cls) -> bool:
        """Check if enforcement is globally killed."""
        return not cls.ENFORCEMENT_ENABLED
