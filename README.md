# genai-agent-orchestrator

The cognitive core of the GenAI Platform. This service is responsible for:
- Accepting user requests
- **Session-aware** context management
- **Policy-driven** planning and routing
- **Cost-aware** execution with selective enforcement
- **SLA-based** classification and progressive rollout
- Orchestrating specialized agents strategies
- Validating, analyzing, and evaluating outputs
- Execution tracing and audit logging

## Architecture

This service follows a **Strict Flat Layout** (No `src/`) and uses **FastAPI** + **LangChain**.

### End-to-End Flow
```
Request → SLA Classify → Memory → Planner (Policy) → Executor (Cost Guard) → Agent → Analyst → Validator → Evaluator → Trace
```

### Layers
- **app/**: API Gateway (FastAPI). No business logic.
- **orchestration/**: The "Brain". `OrchestrationPlanner` applies policy. `Executor` runs plans with tracing.
- **agents/**: Stateless specialists (`Planner`, `Retrieval`, `General`, `Critic`, `Analyst`, `Validator`, `Evaluator`).
- **policy/**: Business rules engine (`Evaluator`, `Simulator`). Checks cost, latency, quality.
- **cost/**: Cost estimation and pricing models (`Estimator`).
- **sla/**: Tier classification (`Classifier`) and Offline Simulation (`Simulator`).
- **enforcement/**: Governance layer. Config (`Kill Switch`), Audit logging, Canary rollout, Graduation evaluator.
- **validation/**: Outcome validation and drift reporting.
- **memory/**: Session-scoped ephemeral context (`SessionStore`).
- **llm/**: LangChain adapter (isolated). Never leaks LangChain objects.
- **mcp/tools/**: MCP tool abstractions (`Calculator`, `Retrieval`).
- **observability/**: Execution tracing (`ExecutionTrace`, `TraceCollector`).
- **evaluation/**: Offline evaluation persistence (`FileEvaluationStore`).

### Architecture Documentation
For detailed architectural references, see:
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System diagram, planes, data flow, enforcement lifecycle, invariants
- **[DECISION_LOG.md](DECISION_LOG.md)** — Why architectural decisions were made
- **[EXTENSION_POINTS.md](EXTENSION_POINTS.md)** — Allowed extensions and hard prohibitions
- **[KNOWLEDGE.md](KNOWLEDGE.md)** — Comprehensive knowledge base

## Key Features

### 🔍 Policy & Cost Guard
Selective enforcement based on run-time risks:
- **Policy Evaluator**: Checks metadata against rules (e.g., "cost > $0.05", "latency > 2s").
- **Cost Guard**: If policy warns about cost, Planner enforces `prefer_cost_efficient` strategy.
- **Trace Visibility**: All enforcement actions are recorded in `policy_enforcement` metadata.

### 📊 SLA & Canary Rollout
Tiered service levels with progressive enforcement:
- **Classification**: Requests classified as `free`, `standard`, or `premium`.
- **Simulation**: Offline `SLASimulator` to predict impact of limits.
- **Canary Enforcement**: safely roll out enforcement to a % of traffic (e.g. 5% of Free Tier).
- **Audit**: Skipped canary requests are auditable.

### 🧠 Session Memory
Short-term conversational context:
- Stores recent turns in-memory.
- Injected into prompt construction for continuity.
- Automatically cleared per session (No long-term persistence).

### 🛡️ Governance
Centralized control plane:
- **Global Kill Switch**: `GENAI_ENFORCEMENT_ENABLED` env var disables all enforcement.
- **Audit Logs**: Structured `EnforcementAudit` records for every intervention.

### 🎓 Graduation Evaluator
Progressive enforcement lifecycle:
- **Simulate**: Offline policy impact analysis before activation.
- **Canary**: 5% rollout with deterministic sampling.
- **Validate**: Compare predicted vs actual outcomes (drift report).
- **Graduate**: GRADUATE / HOLD / ROLLBACK recommendations based on thresholds.

### ⚡ Execution Tracing
Rich metadata for every request:
```json
{
  "routing": {
    "selected_agent": "general",
    "policy_enforcement": {
      "type": "cost_guard",
      "applied": true,
      "reason": "policy_warn_high_cost"
    },
    "canary": {"eligible": true, "sampled": true}
  },
  "sla": {"tier": "free"},
  "estimated_cost_usd": 0.00005
}
```

### 🛡️ Planner Stability (New)
Robust routing logic that ensures:
- **Determinism**: Identical inputs always yield identical routes.
- **Fail-Safe**: Malformed or empty inputs default to `general` agent.
- **Error Recovery**: Internal planner errors are caught and safe fallback is applied.
- **Zero-Crash Policy**: Planner routing never blocks execution.

## API

### POST /v1/orchestrate

Single entry point for all GenAI requests.

**Request:**
```json
{
  "query": "What is Python?",
  "user_id": "user-123",
  "session_id": "session-456"
}
```

**Response:**
```json
{
  "output": "Python is a high-level programming language...",
  "trace_id": "abc-123",
  "metadata": { ... }
}
```

## Development

### Prerequisites
- Python 3.11+
- Azure OpenAI credentials (see `.env.example`)

### Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Running
```bash
uvicorn app.main:app --reload
```

### Verification
```bash
# E2E flow tests
.venv/bin/python tests/test_e2e_flow.py

# Offline Simulation
.venv/bin/python -c "from sla.simulator import SLASimulator..."
```

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `enable_validation` | True | Run output validation |
| `enable_analysis` | True | Run output analysis |
| `enable_evaluation` | True | Run quality evaluation |
| `enable_tracing` | True | Emit execution traces |
| `enable_evaluation_persistence` | True | Persist to JSONL |
| `GENAI_ENFORCEMENT_ENABLED` | True | Master Kill Switch (Env Var) |
