"""
Policy Evaluator

Evaluates execution traces against policy rules.
Read-only - observes only, does not act.

DESIGN RULES:
- Deterministic evaluation
- Never throws (graceful failure)
- Returns structured result
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from policy.rules import PolicyConfig, DEFAULT_CONFIG, POLICY_RULES


@dataclass
class PolicyResult:
    """Result of policy evaluation."""
    status: str  # "pass" | "warn" | "fail"
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checked_rules: int = 0
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "violations": self.violations,
            "warnings": self.warnings,
            "checked_rules": self.checked_rules,
        }


def evaluate_policy(
    metadata: Dict[str, Any],
    config: Optional[PolicyConfig] = None,
) -> PolicyResult:
    """
    Evaluate trace metadata against policy rules.
    
    Args:
        metadata: Execution trace metadata
        config: Policy configuration (uses DEFAULT_CONFIG if not provided)
        
    Returns:
        PolicyResult with status, violations, and warnings
    """
    config = config or DEFAULT_CONFIG
    
    if not config.enabled:
        return PolicyResult(status="pass", enabled=False, checked_rules=0)
    
    try:
        violations: List[str] = []
        warnings: List[str] = []
        checked = 0
        
        # Cost policy
        if config.cost_policy_enabled:
            cost = metadata.get("estimated_cost_usd", 0.0)
            
            if cost > config.max_cost_usd:
                violations.append("high_cost")
            elif cost > config.warn_cost_usd:
                warnings.append("elevated_cost")
            checked += 1
        
        # Score policy
        if config.score_policy_enabled:
            evaluation = metadata.get("evaluation", {})
            score = evaluation.get("score") if isinstance(evaluation, dict) else None
            
            if score is not None:
                if score < config.min_evaluation_score:
                    violations.append("low_score")
                elif score < config.warn_evaluation_score:
                    warnings.append("marginal_score")
            checked += 1
        
        # Latency policy
        if config.latency_policy_enabled:
            latency = metadata.get("latency_ms", 0)
            
            if latency > config.max_latency_ms:
                violations.append("high_latency")
            elif latency > config.warn_latency_ms:
                warnings.append("elevated_latency")
            checked += 1
        
        # Validation policy
        if config.validation_policy_enabled and config.require_valid_output:
            validation = metadata.get("validation", {})
            is_valid = validation.get("is_valid") if isinstance(validation, dict) else True
            
            if is_valid is False:
                violations.append("invalid_output")
            checked += 1
        
        # Determine overall status
        if violations:
            status = "fail"
        elif warnings:
            status = "warn"
        else:
            status = "pass"
        
        return PolicyResult(
            status=status,
            violations=violations,
            warnings=warnings,
            checked_rules=checked,
        )
        
    except Exception as e:
        # Never throw - return error result
        return PolicyResult(
            status="error",
            violations=[f"evaluation_error: {str(e)}"],
            checked_rules=0,
        )
