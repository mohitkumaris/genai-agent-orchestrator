# Extension Points

> **Purpose**: Defines exactly where the platform can be extended and what is forbidden.  
> **Goal**: Guide future changes without architectural drift.

---

## Table of Contents

1. [Enforcement Rules](#1-enforcement-rules)
2. [Memory Expansion](#2-memory-expansion)
3. [Agents](#3-agents)
4. [Policy Rules](#4-policy-rules)
5. [Observability](#5-observability)
6. [Future Autonomy](#6-future-autonomy)
7. [Hard Prohibitions](#7-hard-prohibitions)

---

## 1. Enforcement Rules

### ✅ Allowed Extensions

| Extension | Location | Example |
|-----------|----------|---------|
| Add new enforcement rule | `enforcement/config.py` → `ENABLED_RULES` | `"safety_guard"`, `"compliance_guard"` |
| Define rule thresholds | `policy/rules.py` → `PolicyConfig` | `max_safety_score: float` |
| Integrate rule in planner | `orchestration/planner.py` → `_compute_policy_hints()` | Check new policy warning/violation |

### How to Add a New Rule

1. **Define the rule ID**
   ```python
   # enforcement/config.py
   ENABLED_RULES: Set[str] = {
       "cost_guard",
       "safety_guard",  # NEW
   }
   ```

2. **Add policy thresholds**
   ```python
   # policy/rules.py
   class PolicyConfig:
       safety_policy_enabled: bool = True
       min_safety_score: float = 0.8
       warn_safety_score: float = 0.9
   ```

3. **Add policy evaluation**
   ```python
   # policy/evaluator.py
   if config.safety_policy_enabled:
       safety = metadata.get("safety_score")
       if safety < config.min_safety_score:
           violations.append("low_safety")
   ```

4. **Add enforcement in planner**
   ```python
   # orchestration/planner.py
   if "low_safety" in violations:
       hint = "safety_sensitive"
       if EnforcementConfig.is_enabled("safety_guard"):
           enforcement = PolicyEnforcement(...)
   ```

5. **Add to simulation**
   ```python
   # policy/simulator.py
   # Add safety checks to classification logic
   ```

### Constraints
- Rule ID must be registered in `ENABLED_RULES`
- Rule must follow simulate → canary → validate → graduate lifecycle
- Rule must be auditable via `observability/collector.py`

---

## 2. Memory Expansion

### ✅ Allowed Extensions

| Extension | Location | Purpose |
|-----------|----------|---------|
| Add session memory type | `memory/types.py` | New memory category (e.g., `UserPreferences`) |
| Extend session store | `memory/session_store.py` | New storage mechanism |
| Add memory to trace | `observability/collector.py` | Include memory state in traces |

### Current State
```
memory/
├── __init__.py
├── session_store.py   # Session-scoped key-value store
└── types.py           # Memory type definitions
```

### Extension Pattern
```python
# memory/types.py
@dataclass
class UserPreferences:
    preferred_model: Optional[str] = None
    response_style: str = "concise"
    language: str = "en"

# memory/session_store.py
class SessionStore:
    def get_preferences(self, session_id: str) -> UserPreferences:
        ...
```

### Constraints
- Memory must be **session-scoped** (no persistent user profiles yet)
- Memory access must be **read-only** during execution (write at boundaries)
- Memory must not affect **plan structure** (hints only)

---

## 3. Agents

### ✅ Allowed Extensions

| Extension | Location | Requirements |
|-----------|----------|--------------|
| Add new specialist agent | `agents/` | Extend `BaseAgent`, add to executor registry |
| Add agent-specific prompt | `prompts/agents.yaml` | Follow existing format |
| Add agent to executor | `orchestration/executor.py` | Register in `self.agents` dict |

### How to Add a New Agent

1. **Create agent file**
   ```python
   # agents/summarizer_agent.py
   from agents.base import BaseAgent
   
   class SummarizerAgent(BaseAgent):
       def __init__(self):
           super().__init__("summarizer_agent")
       
       def run(self, *, step: PlanStep, context: MCPContext) -> AgentResult:
           # Implementation
           return AgentResult.success(agent="summarizer", output=...)
   ```

2. **Add prompt configuration**
   ```yaml
   # prompts/agents.yaml
   summarizer_agent:
     system: |
       You are a summarization specialist.
       Produce concise summaries of the provided content.
   ```

3. **Register in executor**
   ```python
   # orchestration/executor.py
   from agents.summarizer_agent import SummarizerAgent
   
   self.agents = {
       "retrieval": RetrievalAgent(),
       "general": GeneralAgent(),
       "critic": CriticAgent(),
       "summarizer": SummarizerAgent(),  # NEW
   }
   ```

4. **Planner can route to it**
   ```python
   # PlannerAgent produces:
   PlanStep(step_id=2, agent_role="summarizer", ...)
   ```

### Constraints
- Agent must be **stateless**
- Agent must accept `PlanStep` and return `AgentResult`
- Agent must NOT call other agents directly
- Agent must NOT make routing decisions

---

## 4. Policy Rules

### ✅ Allowed Extensions

| Extension | Location | Example |
|-----------|----------|---------|
| Add threshold category | `policy/rules.py` → `PolicyConfig` | `max_tokens: int` |
| Add policy check | `policy/evaluator.py` | Token count validation |
| Add simulation metric | `policy/simulator.py` → `SimulationResult` | `tokens_blocked: int` |

### Current Policy Categories
- **Cost**: `max_cost_usd`, `warn_cost_usd`
- **Score**: `min_evaluation_score`, `warn_evaluation_score`
- **Latency**: `max_latency_ms`, `warn_latency_ms`
- **Validation**: `require_valid_output`

### Adding a New Category
```python
# policy/rules.py
class PolicyConfig:
    # Token Policy
    token_policy_enabled: bool = False
    max_tokens: int = 4096
    warn_tokens: int = 3000
```

```python
# policy/evaluator.py
if config.token_policy_enabled:
    tokens = metadata.get("tokens_used", 0)
    if tokens > config.max_tokens:
        violations.append("high_tokens")
    elif tokens > config.warn_tokens:
        warnings.append("elevated_tokens")
```

### Constraints
- Policy must be **configurable** via `PolicyConfig`
- Policy must have **both** violation and warning thresholds
- Policy must be **deterministic** (same input → same result)

---

## 5. Observability

### ✅ Allowed Extensions

| Extension | Location | Purpose |
|-----------|----------|---------|
| Add trace sink | `observability/sink.py` | Export traces to external system |
| Add trace metadata | `observability/collector.py` | Enrich traces with new data |
| Add evaluation metric | `evaluation/store.py` | Persist new evaluation fields |

### Current Sinks
- `ConsoleTraceSink` — Prints to stdout (default)

### Adding a New Sink
```python
# observability/sink.py
class OpenTelemetrySink(TraceSink):
    def emit(self, trace: ExecutionTrace) -> None:
        # Export to OpenTelemetry collector
        span = tracer.start_span(trace.request_id)
        span.set_attributes(trace.to_dict())
        span.end()
```

```python
# Usage in collector
collector = TraceCollector(sink=OpenTelemetrySink())
```

### Constraints
- Sinks must be **non-blocking** (async or fire-and-forget)
- Sinks must **never throw** (graceful failure)
- Trace data must be **immutable** after creation

---

## 6. Future Autonomy

### ⚠️ Controlled Extension Points

These are areas where **autonomy may be added in the future**, but require careful design:

| Area | Current State | Future Consideration |
|------|---------------|---------------------|
| **Re-planning** | Forbidden | May add "safe re-plan" with bounded retries |
| **Agent selection** | Planner-only | May allow critic to suggest agent retry |
| **Memory writes** | Boundary-only | May allow structured memory updates |
| **Tool discovery** | Static registry | May add dynamic MCP tool discovery |

### Guidelines for Autonomy
1. **Bounded**: Any autonomous action must have finite bounds (max retries, timeout)
2. **Observable**: All autonomous decisions logged and traceable
3. **Reversible**: Autonomous actions must be roll-back-able
4. **Opt-in**: Autonomy must be explicitly enabled, never default

---

## 7. Hard Prohibitions

### ❌ Forbidden Changes

| Prohibition | Reason |
|-------------|--------|
| **Enforcement in agents** | Violates central control point; unauditable |
| **Agent-to-agent calls** | Creates circular dependencies; breaks executor control |
| **Plan modification** | Violates immutability invariant; unpredictable |
| **Critic content generation** | Trust violation; hallucination laundering |
| **Blocking on policy error** | Availability kill switch must be fail-open |
| **Non-deterministic sampling** | Breaks reproducibility; debugging impossible |
| **Direct HTTP in agents** | Violates MCP protocol; no observability |
| **Stateful agents** | Horizontal scaling impossible |

### ❌ Forbidden Patterns

```python
# FORBIDDEN: Agent calling another agent
class MyAgent:
    def run(self, step):
        other_result = self.other_agent.run(...)  # NO!

# FORBIDDEN: Modifying plan during execution
class Executor:
    def execute(self, plan):
        plan.steps.append(new_step)  # NO!

# FORBIDDEN: Critic generating content
class CriticAgent:
    def validate(self, result):
        if not result.is_grounded:
            return "Here is a corrected answer..."  # NO!

# FORBIDDEN: Enforcement in agent
class RetrievalAgent:
    def run(self, step):
        if self._should_block():  # NO!
            raise BlockedException()
```

---

## Extension Checklist

Before adding any extension, verify:

- [ ] Does it violate any [Hard Prohibition](#7-hard-prohibitions)?
- [ ] Is it documented in an allowed extension point?
- [ ] Does it follow the simulate → canary → validate → graduate lifecycle (if applicable)?
- [ ] Is it observable (logged, traced, auditable)?
- [ ] Is it stateless (or session-scoped at most)?
- [ ] Is it fail-open (doesn't block on errors)?
- [ ] Is it deterministic (reproducible behavior)?

If any answer is NO, reconsider the design before proceeding.
