"""
Orchestration Planner

Policy influence layer that wraps planner decisions.
Computes policy hints and enriches routing metadata.

DESIGN RULES:
- Policy logic lives HERE, not in agents
- Hints only (mostly), cost guard enforcement allowed (safe override)
- Never blocks requests
- All influence visible in traces
"""


from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
import hashlib

from agents.planner_agent import PlannerAgent, PlannerDecision
from enforcement.config import EnforcementConfig


@dataclass
class PolicyEnforcement:
    """Explicit policy enforcement action."""
    type: str  # e.g., "cost_guard"
    applied: bool
    reason: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EnrichedRoutingDecision:
    """
    Routing decision enriched with policy hints and enforcement.
    
    This is the output from orchestration layer.
    """
    selected_agent: str
    reason: str
    policy_hint: Optional[str] = None
    policy_hint: Optional[str] = None
    policy_influenced: bool = False
    enforcement: Optional[PolicyEnforcement] = None
    enforcement: Optional[PolicyEnforcement] = None
    enforcement_skipped: bool = False
    canary: Optional[Dict[str, bool]] = None
    
    def to_metadata(self) -> Dict[str, Any]:
        """Convert to routing metadata format."""
        meta = {
            "selected_agent": self.selected_agent,
            "reason": self.reason,
            "policy_hint": self.policy_hint,
            "policy_influenced": self.policy_influenced,
            "policy_influenced": self.policy_influenced,
            "enforcement_skipped": self.enforcement_skipped,
            "canary": self.canary,
        }
        if self.enforcement:
            meta["policy_enforcement"] = self.enforcement.to_dict()
        return meta


class OrchestrationPlanner:
    """
    Orchestration-level planner with policy influence.
    
    Wraps PlannerAgent and adds policy hints based on context.
    
    Flow:
        Prompt → PlannerAgent → Base Decision
                              ↓
        Policy Context → OrchestrationPlanner → Enriched Decision (with hints)
    """
    

    def __init__(self, enable_policy_influence: bool = True):
        """
        Initialize orchestration planner.
        
        Args:
            enable_policy_influence: Whether to compute policy hints
        """
        self._planner = PlannerAgent()
        self._policy_influence_enabled = enable_policy_influence
    
    def plan(
        self,
        prompt: str,
        policy_context: Optional[Dict[str, Any]] = None,
    ) -> EnrichedRoutingDecision:
        """
        Plan routing with optional policy influence.
        
        Args:
            prompt: User prompt
            policy_context: Optional policy evaluation result
            
        Returns:
            EnrichedRoutingDecision with policy hints
        """
        # Step 1: Get base routing decision from agent
        base_decision = self._planner.plan(prompt)
        
        # Step 2: Compute policy hints & enforcement (orchestration layer)
        policy_hint = None
        policy_influenced = False
        policy_hint = None
        policy_influenced = False
        enforcement = None
        enforcement_skipped = False
        
        if self._policy_influence_enabled and policy_context:
            policy_hint, policy_influenced, enforcement, enforcement_skipped, canary_meta = self._compute_policy_hints(policy_context, prompt)
        
        return EnrichedRoutingDecision(
            selected_agent=base_decision.selected_agent,
            reason=base_decision.reason,
            policy_hint=policy_hint,
            policy_influenced=policy_influenced,
            enforcement=enforcement,
            enforcement_skipped=enforcement_skipped,
            canary=canary_meta
        )
    
    def _compute_policy_hints(
        self,
        policy_context: Dict[str, Any],
        prompt: str,
    ) -> tuple[Optional[str], bool, Optional[PolicyEnforcement], bool, Optional[Dict[str, bool]]]:
        """
        Compute policy-based hints and enforcement.
        
        RULES:
        - Hints only, NO blocking
        - Cost Guard: Can override preferences if enabled and warning active
        
        Returns:
            (policy_hint, policy_influenced, enforcement, enforcement_skipped, canary_meta) tuple
        """
        status = policy_context.get("status")
        violations = policy_context.get("violations", [])
        warnings = policy_context.get("warnings", [])
        
        hint = None
        influenced = False
        enforcement = None
        enforcement_skipped = False
        canary_meta = None
        
        if status == "fail":
            # Log observation, but do NOT block
            if "high_cost" in violations:
                hint = "cost_sensitive"
                influenced = True
            elif "low_score" in violations:
                hint = "quality_sensitive"
                influenced = True
            elif "high_latency" in violations:
                hint = "latency_sensitive"
                influenced = True
            else:
                hint = "review_recommended"
                influenced = True
                
        elif status == "warn":
            if "elevated_cost" in warnings:
                hint = "prefer_cost_efficient"
                influenced = True
                
                # STRICT Enforcement Rule: Cost Guard
                rule_id = "cost_guard"
                
                # Canary Logic
                # Check if we should enforce based on canary config
                canary_cfg = EnforcementConfig.CANARY_ENFORCEMENT
                should_enforce_rule = False
                
                if EnforcementConfig.is_enabled(rule_id):
                    if canary_cfg.get("enabled"):
                        # Canary Mode: Only enforce if Tier matches and Sampled
                        # Note: We assume Tier 'free' as default for now since planner lacks SLA context
                        # In real world, we'd need Tier passed in.
                        current_tier = "free" 
                        target_tier = canary_cfg.get("tier", "free")
                        
                        if current_tier == target_tier:
                            # Deterministic Sampling based on Prompt Hash
                            # (Proxy for request_id which is unavailable in planner)
                            h_val = int(hashlib.sha256(prompt.encode("utf-8")).hexdigest(), 16)
                            sampled = (h_val % 100) < canary_cfg.get("percentage", 0)
                            
                            canary_meta = {
                                "eligible": True,
                                "sampled": sampled,
                                "tier": current_tier
                            }
                            
                            if sampled:
                                should_enforce_rule = True
                            else:
                                enforcement_skipped = True
                        else:
                            # Not target tier - skip enforcement
                            enforcement_skipped = True
                    else:
                        # Non-Canary (Standard) Mode: Enforce if enabled
                        should_enforce_rule = True
                else:
                    enforcement_skipped = True
                    
                if should_enforce_rule:
                    enforcement = PolicyEnforcement(
                        type=rule_id,
                        applied=True,
                        reason="policy_warn_high_cost"
                    )
                
            elif "marginal_score" in warnings:
                hint = "prefer_quality"
                influenced = True
            elif "elevated_latency" in warnings:
                hint = "prefer_fast"
                influenced = True
        
        return hint, influenced, enforcement, enforcement_skipped, canary_meta
