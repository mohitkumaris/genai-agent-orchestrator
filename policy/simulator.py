"""
Policy Simulator

Offline simulation to evaluate policy impact before enforcement.
Answers "what would happen if..." questions.

DESIGN RULES:
- Offline only (no runtime hooks)
- Idempotent
- Configurable thresholds
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from policy.rules import PolicyConfig, DEFAULT_CONFIG


@dataclass
class SimulationResult:
    """Result of policy simulation."""
    total_requests: int
    would_pass: int
    would_warn: int
    would_block: int
    
    # Cost analysis
    total_cost_usd: float
    blocked_cost_usd: float
    avg_cost_blocked_usd: float
    
    # Quality analysis
    avg_score_all: float
    avg_score_blocked: float
    avg_score_passed: float
    
    # Trade-off metrics
    block_rate: float
    warn_rate: float
    quality_loss: float  # avg_score_blocked - avg_score_passed (negative = blocking low quality)
    
    # Per-rule breakdown
    violations_by_rule: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "would_pass": self.would_pass,
            "would_warn": self.would_warn,
            "would_block": self.would_block,
            "block_rate": f"{self.block_rate:.1%}",
            "warn_rate": f"{self.warn_rate:.1%}",
            "total_cost_usd": self.total_cost_usd,
            "blocked_cost_usd": self.blocked_cost_usd,
            "avg_cost_blocked_usd": self.avg_cost_blocked_usd,
            "avg_score_all": self.avg_score_all,
            "avg_score_blocked": self.avg_score_blocked,
            "avg_score_passed": self.avg_score_passed,
            "quality_loss": self.quality_loss,
            "violations_by_rule": self.violations_by_rule,
        }
    
    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            "=" * 50,
            "POLICY SIMULATION RESULTS",
            "=" * 50,
            f"Total requests:     {self.total_requests}",
            f"Would pass:         {self.would_pass} ({100*self.would_pass/self.total_requests:.1f}%)" if self.total_requests else "",
            f"Would warn:         {self.would_warn} ({self.warn_rate:.1%})" if self.total_requests else "",
            f"Would block:        {self.would_block} ({self.block_rate:.1%})" if self.total_requests else "",
            "",
            "COST ANALYSIS",
            f"Total cost:         ${self.total_cost_usd:.6f}",
            f"Blocked cost:       ${self.blocked_cost_usd:.6f}",
            f"Avg cost (blocked): ${self.avg_cost_blocked_usd:.6f}",
            "",
            "QUALITY ANALYSIS",
            f"Avg score (all):    {self.avg_score_all:.3f}",
            f"Avg score (blocked):{self.avg_score_blocked:.3f}",
            f"Avg score (passed): {self.avg_score_passed:.3f}",
            f"Quality delta:      {self.quality_loss:+.3f}",
            "",
            "VIOLATIONS BY RULE",
        ]
        for rule, count in self.violations_by_rule.items():
            lines.append(f"  {rule}: {count}")
        lines.append("=" * 50)
        return "\n".join(lines)


def simulate(
    records: List[Dict[str, Any]],
    config: Optional[PolicyConfig] = None,
) -> SimulationResult:
    """
    Simulate policy outcomes on historical records.
    
    Args:
        records: List of evaluation records from JSONL
        config: Policy configuration to simulate
        
    Returns:
        SimulationResult with breakdown
    """
    config = config or DEFAULT_CONFIG
    
    if not records:
        return SimulationResult(
            total_requests=0,
            would_pass=0, would_warn=0, would_block=0,
            total_cost_usd=0, blocked_cost_usd=0, avg_cost_blocked_usd=0,
            avg_score_all=0, avg_score_blocked=0, avg_score_passed=0,
            block_rate=0, warn_rate=0, quality_loss=0,
        )
    
    pass_list = []
    warn_list = []
    block_list = []
    violations_by_rule: Dict[str, int] = {}
    
    for record in records:
        violations = []
        warnings = []
        
        cost = record.get("estimated_cost_usd", 0) or 0
        score = record.get("evaluation_score")
        latency = record.get("latency_ms", 0) or 0
        is_valid = record.get("validation_valid", True)
        
        # Cost checks
        if config.cost_policy_enabled:
            if cost > config.max_cost_usd:
                violations.append("high_cost")
            elif cost > config.warn_cost_usd:
                warnings.append("elevated_cost")
        
        # Score checks
        if config.score_policy_enabled and score is not None:
            if score < config.min_evaluation_score:
                violations.append("low_score")
            elif score < config.warn_evaluation_score:
                warnings.append("marginal_score")
        
        # Latency checks
        if config.latency_policy_enabled:
            if latency > config.max_latency_ms:
                violations.append("high_latency")
            elif latency > config.warn_latency_ms:
                warnings.append("elevated_latency")
        
        # Validation checks
        if config.validation_policy_enabled and is_valid is False:
            violations.append("invalid_output")
        
        # Track violations
        for v in violations:
            violations_by_rule[v] = violations_by_rule.get(v, 0) + 1
        
        # Classify outcome
        if violations:
            block_list.append(record)
        elif warnings:
            warn_list.append(record)
        else:
            pass_list.append(record)
    
    # Calculate metrics
    total = len(records)
    
    all_scores = [r["evaluation_score"] for r in records if r.get("evaluation_score") is not None]
    blocked_scores = [r["evaluation_score"] for r in block_list if r.get("evaluation_score") is not None]
    passed_scores = [r["evaluation_score"] for r in pass_list if r.get("evaluation_score") is not None]
    
    all_costs = [r.get("estimated_cost_usd", 0) or 0 for r in records]
    blocked_costs = [r.get("estimated_cost_usd", 0) or 0 for r in block_list]
    
    avg_score_all = sum(all_scores) / len(all_scores) if all_scores else 0
    avg_score_blocked = sum(blocked_scores) / len(blocked_scores) if blocked_scores else 0
    avg_score_passed = sum(passed_scores) / len(passed_scores) if passed_scores else avg_score_all
    
    return SimulationResult(
        total_requests=total,
        would_pass=len(pass_list),
        would_warn=len(warn_list),
        would_block=len(block_list),
        total_cost_usd=sum(all_costs),
        blocked_cost_usd=sum(blocked_costs),
        avg_cost_blocked_usd=sum(blocked_costs) / len(blocked_costs) if blocked_costs else 0,
        avg_score_all=avg_score_all,
        avg_score_blocked=avg_score_blocked,
        avg_score_passed=avg_score_passed,
        block_rate=len(block_list) / total if total else 0,
        warn_rate=len(warn_list) / total if total else 0,
        quality_loss=avg_score_blocked - avg_score_passed,
        violations_by_rule=violations_by_rule,
    )


def compare_policies(
    records: List[Dict[str, Any]],
    current: PolicyConfig,
    proposed: PolicyConfig,
) -> Dict[str, Any]:
    """
    Compare two policy configurations.
    
    Returns impact analysis of switching from current to proposed.
    """
    current_result = simulate(records, current)
    proposed_result = simulate(records, proposed)
    
    return {
        "current": current_result.to_dict(),
        "proposed": proposed_result.to_dict(),
        "delta": {
            "block_rate_change": proposed_result.block_rate - current_result.block_rate,
            "blocked_cost_change": proposed_result.blocked_cost_usd - current_result.blocked_cost_usd,
            "quality_loss_change": proposed_result.quality_loss - current_result.quality_loss,
        }
    }


# CLI entry point
if __name__ == "__main__":
    import argparse
    from evaluation.reader import load_records
    
    parser = argparse.ArgumentParser(description="Policy Simulation")
    parser.add_argument("--path", default="evaluations.jsonl", help="JSONL file path")
    parser.add_argument("--max-cost", type=float, help="Override max cost threshold")
    parser.add_argument("--min-score", type=float, help="Override min score threshold")
    parser.add_argument("--max-latency", type=int, help="Override max latency (ms)")
    
    args = parser.parse_args()
    
    # Load records
    records = load_records(args.path)
    
    if not records:
        print("No records found.")
        exit(1)
    
    # Build config
    config = PolicyConfig()
    if args.max_cost:
        config.max_cost_usd = args.max_cost
    if args.min_score:
        config.min_evaluation_score = args.min_score
    if args.max_latency:
        config.max_latency_ms = args.max_latency
    
    # Run simulation
    result = simulate(records, config)
    print(result.summary())
