"""
Policy Rules

Declarative policy configuration for governance.
Rules are evaluated against execution traces.

DESIGN RULES:
- Declarative (data, not code)
- Configurable thresholds
- Deterministic evaluation
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class PolicyConfig:
    """
    Policy configuration with tunable thresholds.
    
    All thresholds can be adjusted without code changes.
    """
    
    # Cost thresholds (USD)
    max_cost_usd: float = 0.001  # $0.001 per request
    warn_cost_usd: float = 0.0005  # Warn above $0.0005
    
    # Quality thresholds
    min_evaluation_score: float = 0.5  # Fail below 0.5
    warn_evaluation_score: float = 0.6  # Warn below 0.6
    
    # Latency thresholds (ms)
    max_latency_ms: int = 30000  # 30 seconds
    warn_latency_ms: int = 10000  # Warn above 10 seconds
    
    # Validation
    require_valid_output: bool = True  # Fail if validation.is_valid == False
    
    # Enable/disable flags
    enabled: bool = True
    cost_policy_enabled: bool = True
    score_policy_enabled: bool = True
    latency_policy_enabled: bool = True
    validation_policy_enabled: bool = True


# Default configuration (can be overridden)
DEFAULT_CONFIG = PolicyConfig()


@dataclass
class PolicyRule:
    """Definition of a single policy rule."""
    name: str
    description: str
    severity: str  # "fail" | "warn"
    enabled: bool = True


# Define all rules
POLICY_RULES: List[PolicyRule] = [
    PolicyRule(
        name="high_cost",
        description="Request cost exceeds maximum threshold",
        severity="fail",
    ),
    PolicyRule(
        name="elevated_cost",
        description="Request cost is above warning threshold",
        severity="warn",
    ),
    PolicyRule(
        name="low_score",
        description="Evaluation score is below minimum threshold",
        severity="fail",
    ),
    PolicyRule(
        name="marginal_score",
        description="Evaluation score is below warning threshold",
        severity="warn",
    ),
    PolicyRule(
        name="high_latency",
        description="Request latency exceeds maximum threshold",
        severity="fail",
    ),
    PolicyRule(
        name="elevated_latency",
        description="Request latency is above warning threshold",
        severity="warn",
    ),
    PolicyRule(
        name="invalid_output",
        description="Output failed validation",
        severity="fail",
    ),
]
