# genai-agent-orchestrator

The cognitive core of the GenAI Platform. This service is responsible for:
- Accepting user requests
- Planning execution strategies (PlannerAgent)
- Routing to specialized agents via OrchestrationRouter
- Orchestrating multi-step reasoning (OrchestrationExecutor)
- Validating and evaluating outputs
- Invoking tools via MCP (Model Context Protocol)
- Execution tracing and evaluation persistence

## Architecture

This service follows a **Strict Flat Layout** (No `src/`) and uses **FastAPI** + **LangChain**.

### End-to-End Flow
```
Request → Planner → Executor → Agent → Analyst → Validator → Evaluator → Trace → Response
```

### Layers
- **app/**: API Gateway (FastAPI). No business logic.
- **orchestration/**: The "Brain". `OrchestrationRouter` controls flow. `Executor` runs plans with tracing.
- **agents/**: Stateless specialists (`Planner`, `Retrieval`, `General`, `Critic`, `Analyst`, `Validator`, `Evaluator`).
- **llm/**: LangChain adapter (isolated). Never leaks LangChain objects.
- **mcp/tools/**: MCP tool abstractions (`Calculator`, `Retrieval`).
- **observability/**: Execution tracing (`ExecutionTrace`, `TraceSink`, `TraceCollector`).
- **evaluation/**: Offline evaluation persistence (`EvaluationStore`, `FileEvaluationStore`).
- **schemas/**: Domain models (`AgentResult`, `FinalResponse`).

## Key Features

### LangChain Isolation
LangChain is used **only** in `llm/langchain_adapter.py`:
```python
from llm.langchain_adapter import generate, generate_with_tools, generate_with_context
output, metadata = generate(prompt)
```
- No LangChain imports in agents
- Metadata returned as plain dict
- Provider-agnostic interface

### MCP Tools
Tools are registered via `ToolRegistry` with permission-based access:
```python
from mcp.tools.registry import ToolRegistry, bootstrap_tools
bootstrap_tools()  # Registers calculator, retrieval tools
registry.list_for_agent("general")  # Returns allowed tools
```

### RAG as a Tool
Retrieval is implemented as an MCP tool, not orchestration logic:
```python
# RetrievalAgent uses tool → LLM pattern
retrieval_tool.run({"query": prompt, "k": 3})  # Get documents
generate_with_context(prompt, documents)       # Ground response
```

### Execution Tracing
Every request produces an `ExecutionTrace`:
```
[TRACE] ✓ abc123...
  Agent: general | Latency: 3312ms
  Metadata: routing, analysis, validation, evaluation
```

### Evaluation Persistence
Evaluation signals are persisted to JSONL for offline analysis:
```python
from evaluation.file_store import FileEvaluationStore
store = FileEvaluationStore()
store.get_statistics()  # {'avg_evaluation_score': 0.775, 'success_rate': 1.0}
```

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
  "is_safe": true,
  "risk_level": "low",
  "recommendation": "proceed",
  "issues": [],
  "trace_id": "abc-123"
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

# Tool integration tests
.venv/bin/python tests/test_tools.py
```

## Configuration Flags

| Flag | Default | Description |
|------|---------|-------------|
| `enable_validation` | True | Run output validation |
| `enable_analysis` | True | Run output analysis |
| `enable_evaluation` | True | Run quality evaluation |
| `enable_tracing` | True | Emit execution traces |
| `enable_evaluation_persistence` | True | Persist to JSONL |
