# GenAI Platform Architecture

> **Version**: 1.0  
> **Status**: FROZEN — Canonical Reference  
> **Last Updated**: 2026-02-04

This document defines the architectural intent of the GenAI Agent Orchestrator. It serves as the authoritative reference for all future work.

---

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            GENAI PLATFORM ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                         EXECUTION PLANE                                   │  │
│  │  ┌─────────┐   ┌──────────────┐   ┌──────────────┐   ┌───────────────┐   │  │
│  │  │ Planner │ → │   Executor   │ → │   Agents     │ → │    Critic     │   │  │
│  │  │ Agent   │   │              │   │ (Stateless)  │   │  (Evaluator)  │   │  │
│  │  └─────────┘   └──────────────┘   └──────────────┘   └───────────────┘   │  │
│  │       │                                                      │           │  │
│  │       ▼                                                      ▼           │  │
│  │  ExecutionPlan                                          CriticResult     │  │
│  │  (Immutable)                                            (Validation)     │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                            │
│                                    ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                         CONTROL PLANE                                     │  │
│  │  ┌─────────────────┐   ┌─────────────────┐   ┌───────────────────────┐   │  │
│  │  │ Orchestration   │   │     Policy      │   │       SLA             │   │  │
│  │  │ Router          │   │    Evaluator    │   │    Classifier         │   │  │
│  │  │                 │   │   (Read-only)   │   │                       │   │  │
│  │  └─────────────────┘   └─────────────────┘   └───────────────────────┘   │  │
│  │           │                     │                       │                │  │
│  │           └─────────────────────┴───────────────────────┘                │  │
│  │                                 │                                        │  │
│  │                                 ▼                                        │  │
│  │                      EnrichedRoutingDecision                             │  │
│  │                      (+ policy hints, SLA tier)                          │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                            │
│                                    ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                       GOVERNANCE PLANE                                    │  │
│  │  ┌─────────────────┐   ┌─────────────────┐   ┌───────────────────────┐   │  │
│  │  │   Enforcement   │   │    Graduation   │   │    Canary             │   │  │
│  │  │   Config        │   │    Evaluator    │   │    Controller         │   │  │
│  │  │  (Kill Switch)  │   │ (GRADUATE/HOLD) │   │   (5% Sampling)       │   │  │
│  │  └─────────────────┘   └─────────────────┘   └───────────────────────┘   │  │
│  │           │                     │                       │                │  │
│  │           └─────────────────────┴───────────────────────┘                │  │
│  │                                 │                                        │  │
│  │                                 ▼                                        │  │
│  │                        PolicyEnforcement                                 │  │
│  │                      (cost_guard applied)                                │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                            │
│                                    ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                          OPS PLANE                                        │  │
│  │  ┌─────────────────┐   ┌─────────────────┐   ┌───────────────────────┐   │  │
│  │  │     Trace       │   │   Enforcement   │   │     Evaluation        │   │  │
│  │  │    Collector    │   │     Audit       │   │       Store           │   │  │
│  │  │                 │   │                 │   │                       │   │  │
│  │  └─────────────────┘   └─────────────────┘   └───────────────────────┘   │  │
│  │           │                     │                       │                │  │
│  │           └─────────────────────┴───────────────────────┘                │  │
│  │                                 │                                        │  │
│  │                                 ▼                                        │  │
│  │                         ExecutionTrace                                   │  │
│  │                    (+ cost, policy, SLA, canary)                         │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Architectural Planes

### 1. Execution Plane

**Purpose**: Stateless request-response processing.

| Component | Role | Key Invariant |
|-----------|------|---------------|
| **PlannerAgent** | Creates execution plans | Runs **once** per request; produces **immutable** plans |
| **OrchestrationExecutor** | Runs plan steps sequentially | Never modifies plans; controls all agent calls |
| **Specialist Agents** | Execute individual steps | Stateless; execute only; no agent-to-agent communication |
| **CriticAgent** | Validates outputs | Evaluates only; never generates or rewrites content |

**Data Flow**:
```
ServiceRequest → PlannerAgent → ExecutionPlan → Executor → AgentResult → Critic → FinalResponse
```

### 2. Control Plane

**Purpose**: Orchestration logic that shapes execution without blocking it.

| Component | Role | Key Invariant |
|-----------|------|---------------|
| **OrchestrationPlanner** | Wraps planner with policy hints | Produces **hints only**, never blocks |
| **PolicyEvaluator** | Evaluates traces against rules | **Read-only**, deterministic, never throws |
| **SLAClassifier** | Classifies requests by tier | Deterministic; currently defaults to `free` |

**Output**: `EnrichedRoutingDecision` with policy hints, SLA tier, and optional enforcement action.

### 3. Governance Plane

**Purpose**: Controlled, progressive enforcement of policies.

| Component | Role | Key Invariant |
|-----------|------|---------------|
| **EnforcementConfig** | Global kill switch + rule toggles | Master switch disables ALL enforcement |
| **Canary Controller** | Progressive rollout (5% sampling) | Deterministic sampling via prompt hash |
| **GraduationEvaluator** | Decides GRADUATE / HOLD / ROLLBACK | Based on drift, score delta, critical audits |

**Enforcement Lifecycle**:
```
SIMULATE → CANARY → VALIDATE → GRADUATE
    ↓         ↓         ↓          ↓
 Offline   5% Live   Compare    Full
 Impact    Rollout   Outcomes   Activation
```

### 4. Ops Plane

**Purpose**: Observability, persistence, and auditability.

| Component | Role | Key Invariant |
|-----------|------|---------------|
| **TraceCollector** | Coordinates trace lifecycle | Never throws; graceful failure |
| **EnforcementAudit** | Logs all enforcement actions | Every enforcement visible in audit log |
| **EvaluationStore** | Persists evaluation data (JSONL) | Append-only; used for simulation |

---

## Request → Response Data Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          END-TO-END DATA FLOW                              │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  1. ENTRY                                                                  │
│     FastAPI → ServiceRequest → OrchestrationRouter                         │
│                                                                            │
│  2. PLANNING                                                               │
│     OrchestrationPlanner.plan()                                            │
│       ├── PlannerAgent.plan() → Base Decision                              │
│       ├── PolicyEvaluator.evaluate() → PolicyResult                        │
│       ├── SLAClassifier.classify() → Tier + Limits                         │
│       └── _compute_policy_hints() → Enforcement Decision                   │
│             └── Canary: eligible? sampled? → enforce or skip               │
│                                                                            │
│  3. EXECUTION                                                              │
│     OrchestrationExecutor.execute_plan()                                   │
│       ├── For each PlanStep:                                               │
│       │     Agent.run() → AgentResult                                      │
│       └── → ExecutionResult                                                │
│                                                                            │
│  4. VALIDATION                                                             │
│     CriticAgent.validate_from_execution()                                  │
│       └── → CriticResult (is_safe, risk_level, recommendation)             │
│                                                                            │
│  5. ASSEMBLY                                                               │
│     FinalResponse.from_execution()                                         │
│       └── → FinalResponse (with grounding_score, trace_id)                 │
│                                                                            │
│  6. TRACE                                                                  │
│     TraceCollector.capture()                                               │
│       ├── _estimate_cost() → cost_usd                                      │
│       ├── _evaluate_policy() → policy result                               │
│       ├── _classify_sla() → tier                                           │
│       ├── _audit_enforcement() → audit log                                 │
│       └── _save_evaluation() → JSONL persistence                           │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Enforcement Lifecycle

The platform implements progressive enforcement through a controlled lifecycle:

### Phase 1: SIMULATE (Offline)
- **Component**: `policy/simulator.py`
- **Purpose**: Answer "what would happen if..."
- **Input**: Historical evaluation records (JSONL)
- **Output**: SimulationResult (block_rate, warn_rate, quality_loss)
- **Key**: No runtime impact; pure analysis

### Phase 2: CANARY (5% Live)
- **Component**: `enforcement/config.py` → `CANARY_ENFORCEMENT`
- **Purpose**: Test enforcement on small traffic slice
- **Mechanism**: Deterministic sampling via SHA256(prompt) % 100 < percentage
- **Current Config**: `enabled=True, tier="free", percentage=5`
- **Key**: Observable, reversible, tier-scoped

### Phase 3: VALIDATE (Compare)
- **Component**: `validation/report.py` → `DriftReport`
- **Purpose**: Compare predicted vs actual outcomes
- **Metrics**: cost_error_pct, score_error, actual_enforcements
- **Key**: Measures simulation accuracy

### Phase 4: GRADUATE (Scale Up)
- **Component**: `enforcement/graduation_evaluator.py`
- **Purpose**: Decide readiness for full activation
- **Recommendations**: GRADUATE, HOLD, ROLLBACK
- **Thresholds**:
  - `max_drift_pct`: 10%
  - `min_success_rate`: 99%
  - `max_score_delta`: 0.05
  - `max_critical_audits`: 0

---

## Architectural Invariants

These are **non-negotiable** principles that must not be violated:

| # | Invariant | Rationale |
|---|-----------|-----------|
| 1 | **Planner runs once** | No re-planning; predictable execution |
| 2 | **Plans are immutable** | Executor reads, never writes |
| 3 | **No back-edges** | Single-direction flow; no loops |
| 4 | **Agents are stateless** | Horizontally scalable; reproducible |
| 5 | **Critic never generates** | Evaluator only; trust before fluency |
| 6 | **Enforcement is planner-only** | Central control point; never at agent level |
| 7 | **Fail-open by default** | Never block on error; hints only unless explicitly enforced |
| 8 | **All enforcement auditable** | Every enforcement action logged |
| 9 | **Simulation precedes activation** | No enforcement without impact analysis |
| 10 | **MCP for all external calls** | Agents never make direct HTTP calls |

---

## Module Responsibilities

| Directory | Plane | Responsibility |
|-----------|-------|----------------|
| `app/` | - | API Gateway (FastAPI); routing only; no logic |
| `agents/` | Execution | Stateless specialist agents |
| `orchestration/` | Control + Execution | Router, Executor, Planner wrapper |
| `policy/` | Control | Policy rules, evaluator, simulator |
| `sla/` | Control | SLA tiers, limits, classification |
| `enforcement/` | Governance | Config, audit, graduation |
| `validation/` | Governance | Drift reports, outcome validation |
| `observability/` | Ops | Trace collector, sinks |
| `cost/` | Ops | Cost estimation from metadata |
| `evaluation/` | Ops | Evaluation store (JSONL persistence) |
| `schemas/` | - | Shared Pydantic models |
| `mcp_client/` | - | MCP protocol adapter |

---

## File Reference

### Governance Files
- `enforcement/config.py` — Master kill switch, rule toggles, canary config
- `enforcement/graduation_evaluator.py` — GRADUATE/HOLD/ROLLBACK decisions
- `enforcement/graduation_rules.py` — Threshold definitions
- `enforcement/audit.py` — Audit data structures

### Policy Files
- `policy/rules.py` — PolicyConfig with thresholds
- `policy/evaluator.py` — Read-only policy evaluation
- `policy/simulator.py` — Offline simulation engine

### Validation Files
- `validation/report.py` — DriftReport structure

### Observability Files
- `observability/collector.py` — Trace lifecycle coordination
- `observability/trace.py` — ExecutionTrace model
- `observability/sink.py` — TraceSink interface

---

## Summary

The GenAI Agent Orchestrator implements a layered architecture with clear separation:

1. **Execution** handles stateless request processing
2. **Control** shapes decisions through hints without blocking
3. **Governance** enables safe, progressive enforcement rollout
4. **Ops** ensures full observability and auditability

All enforcement follows the **simulate → canary → validate → graduate** lifecycle, ensuring changes are intentional, observable, and reversible.
