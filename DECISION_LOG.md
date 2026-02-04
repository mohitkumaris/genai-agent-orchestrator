# Decision Log

> **Purpose**: Documents *why* architectural decisions were made.  
> **Goal**: Prevent future "why don't we just..." debates.

---

## Table of Contents

1. [Enforcement Location](#1-enforcement-location)
2. [Agent Design](#2-agent-design)
3. [Simulation Before Activation](#3-simulation-before-activation)
4. [Fail-Open Default](#4-fail-open-default)
5. [Canary Sampling](#5-canary-sampling)
6. [Graduation Thresholds](#6-graduation-thresholds)
7. [Plan Immutability](#7-plan-immutability)
8. [Critic Limitations](#8-critic-limitations)

---

## 1. Enforcement Location

### Decision
Enforcement happens **only in the planner**, not in agents or executor.

### Why
| Alternative | Problem |
|-------------|---------|
| Enforce in each agent | Scattered logic; hard to audit; inconsistent behavior |
| Enforce in executor | Too late; plan already committed |
| Enforce at API gateway | No context; can't make intelligent decisions |

### Benefits
- **Single control point**: All enforcement decisions visible in one place
- **Auditability**: One location to log all enforcement actions
- **Reversibility**: Kill switch affects one component
- **Context-aware**: Planner has full request context for decisions

### Code Reference
```
orchestration/planner.py → _compute_policy_hints()
```

---

## 2. Agent Design

### Decision
Agents are **execution-only**. They do not:
- Make routing decisions
- Call other agents directly
- Modify execution plans
- Hold state between requests

### Why
| Alternative | Problem |
|-------------|---------|
| Smart agents that route | Unpredictable flow; debugging nightmare |
| Stateful agents | Horizontal scaling impossible; session affinity required |
| Agent-to-agent calls | Circular dependencies; no central control |

### Benefits
- **Predictability**: Given input X, agent produces output Y
- **Scalability**: Any agent instance can handle any request
- **Testability**: Agents can be unit tested in isolation
- **Observability**: Executor controls all calls; full trace visibility

### Invariant
> Agents receive a `PlanStep`, execute it, return `AgentResult`. Nothing more.

---

## 3. Simulation Before Activation

### Decision
All enforcement rules must be **simulated offline** before live activation.

### Why
| Alternative | Problem |
|-------------|---------|
| Direct activation | Unknown block rate; potential quality regression |
| A/B testing only | Too slow; insufficient coverage |
| Manual review | Doesn't scale; subjective |

### Benefits
- **Impact visibility**: Know block rate before going live
- **Quality analysis**: Understand what gets blocked (good or bad?)
- **Threshold tuning**: Adjust config based on data, not intuition
- **Confidence**: Operators can justify enforcement decisions

### Workflow
```
1. Collect evaluation data (evaluations.jsonl)
2. Run: python -m policy.simulator --path evaluations.jsonl
3. Review: block_rate, warn_rate, quality_loss
4. If acceptable → proceed to canary
5. If not → adjust thresholds, re-simulate
```

### Code Reference
```
policy/simulator.py → simulate()
```

---

## 4. Fail-Open Default

### Decision
The system **never blocks** on infrastructure or policy errors. Default is fail-open.

### Why
| Alternative | Problem |
|-------------|---------|
| Fail-closed | One bug blocks all traffic; catastrophic |
| Partial failure | Inconsistent behavior; hard to debug |

### Benefits
- **Availability**: Service stays up even if governance fails
- **Predictability**: Users always get responses
- **Safety**: Bad enforcement config doesn't kill production
- **Debugging**: Errors logged, traffic continues

### Implementation
```python
# policy/evaluator.py
except Exception as e:
    return PolicyResult(status="error", ...)  # NOT "fail"

# enforcement/config.py
ENFORCEMENT_ENABLED = os.getenv("GENAI_ENFORCEMENT_ENABLED", "true")
# Can be disabled instantly via env var
```

### Invariant
> Policy evaluation errors → status="error", NOT "fail"  
> Enforcement config errors → enforcement skipped, NOT blocking

---

## 5. Canary Sampling

### Decision
Canary uses **deterministic sampling** based on prompt hash, not random sampling.

### Why
| Alternative | Problem |
|-------------|---------|
| Random sampling | Non-reproducible; same request may get different treatment |
| Time-based | Inconsistent testing; can't reproduce issues |
| User-based | Requires auth context not always available |

### Benefits
- **Reproducibility**: Same prompt always gets same treatment
- **Debugging**: Can reproduce exact canary behavior
- **Fairness**: Consistent experience per request type
- **Simplicity**: No external state needed

### Implementation
```python
# orchestration/planner.py
h_val = int(hashlib.sha256(prompt.encode("utf-8")).hexdigest(), 16)
sampled = (h_val % 100) < canary_cfg.get("percentage", 0)
```

### Trade-off
Determinism means some prompts always hit canary, some never do. This is intentional — it makes canary behavior predictable and reproducible.

---

## 6. Graduation Thresholds

### Decision
Graduation from canary to full enforcement requires passing **all** thresholds.

### Why
Conservative by design. Failed graduation is safe; premature graduation is dangerous.

### Current Thresholds
| Threshold | Value | Meaning |
|-----------|-------|---------|
| `max_drift_pct` | 10% | Predicted vs actual enforcement must match within 10% |
| `min_success_rate` | 99% | Less than 1% failure rate |
| `max_score_delta` | 0.05 | Quality can't drop more than 0.05 |
| `max_critical_audits` | 0 | No rollback or critical events during canary |

### Recommendation Logic
```
0 violations → GRADUATE
1 violation → HOLD
2+ violations → ROLLBACK
```

### Code Reference
```
enforcement/graduation_evaluator.py
enforcement/graduation_rules.py
```

---

## 7. Plan Immutability

### Decision
Once `PlannerAgent` produces an `ExecutionPlan`, it is **never modified**.

### Why
| Alternative | Problem |
|-------------|---------|
| Dynamic re-planning | Unpredictable execution; infinite loops possible |
| Step modification | Race conditions; audit trail broken |
| Conditional branches | Complexity explosion; testing nightmare |

### Benefits
- **Predictability**: Plan created = plan executed
- **Auditability**: Can replay exact execution
- **Simplicity**: No plan mutation logic needed
- **Debugging**: Plan ID traces through entire flow

### Implementation
```python
class ExecutionPlan(BaseModel):
    plan_id: str           # Generated once
    steps: List[PlanStep]  # Read-only after creation

# Executor ONLY reads plan.steps
for step in plan.steps:
    await self._execute_step(step, ...)
```

### Invariant
> If re-planning is needed, create a NEW plan. Never mutate existing.

---

## 8. Critic Limitations

### Decision
`CriticAgent` **only validates**. It never:
- Generates content
- Rewrites answers
- Calls tools
- Requests re-execution

### Why
| Alternative | Problem |
|-------------|---------|
| Critic rewrites | Hallucination laundering; bypasses grounding |
| Critic calls tools | Infinite loops; unpredictable side effects |
| Critic triggers re-plan | Back-edge violation; complexity |

### Benefits
- **Trust**: If critic passes output, it passed as-is
- **Transparency**: Output shown = output generated
- **Safety**: Can't inject content post-validation
- **Simplicity**: Critic is pure function: input → CriticResult

### Design Philosophy
> "A blocked answer is better than a hallucinated one."  
> "Trust is more important than fluency."

### Output Structure
```python
class CriticResult:
    is_safe: bool           # Verdict
    risk_level: RiskLevel   # Classification
    recommendation: Recommendation  # PROCEED/WARN/BLOCK
    validated_claims: List[ValidatedClaim]  # Grounding status
    grounding_score: float  # 0.0-1.0
```

### Invariant
> Critic produces structured metadata. Never content.

---

## Future Decision Considerations

When facing "why don't we just..." questions, consult this log first. If the decision isn't documented here, consider:

1. Does it violate any documented invariant?
2. What problem does the alternative solve?
3. What new problems does the alternative create?
4. Can we simulate the impact before committing?

Add new decisions to this log with the same structure:
- **Decision**: What we chose
- **Why**: Comparison with alternatives
- **Benefits**: What we gain
- **Code Reference**: Where it's implemented
