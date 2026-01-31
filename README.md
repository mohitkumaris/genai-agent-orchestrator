# genai-agent-orchestrator

The cognitive core of the GenAI Platform. This service is responsible for:
- Accepting user requests
- Planning execution strategies (PlannerAgent)
- Routing to specialized agents via OrchestrationRouter
- Orchestrating multi-step reasoning (OrchestrationExecutor)
- Validating outputs (CriticAgent)
- Invoking tools via MCP (Model Context Protocol)

## Architecture

This service follows a **Strict Flat Layout** (No `src/`) and uses **FastAPI** + **LangChain**.

### End-to-End Flow
```
Request → Planner → ExecutionPlan → Executor → Critic → FinalResponse
```

### Layers
- **app/**: API Gateway (FastAPI). No business logic.
- **orchestration/**: The "Brain". `OrchestrationRouter` controls the flow. `Executor` runs immutable `ExecutionPlans`.
- **agents/**: Stateless specialists (`Planner`, `Retrieval`, `Critic`).
- **mcp_client/**: Protocol layer for tool invocation.
- **schemas/**: Domain models (`Plan`, `Result`, `CriticResult`, `FinalResponse`).

## API

### POST /v1/orchestrate

Single entry point for all GenAI requests.

> **Current Status:** Pass-through mode for APIM → FastAPI connectivity validation.  
> Returns a static JSON response echoing the input (no agent logic invoked).

**Request:**
```json
{
  "query": "Hello from APIM test",
  "user_id": "user-123",
  "session_id": "session-456"
}
```

**Response (Pass-through mode):**
```json
{
  "request_id": "debug",
  "result": {
    "message": "APIM → FastAPI works",
    "input": "Hello from APIM test"
  }
}
```

**Response (Full orchestration - future):**
```json
{
  "output": "RAG (Retrieval-Augmented Generation) is...",
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
- `genai-mcp-core`

### Setup
```bash
# Create venv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
```

### Running
```bash
uvicorn app.main:app --reload
```

### Verification
Run the pure Python verification suite:
```bash
python3 tests/test_executor_pure.py
python3 tests/test_retrieval_pure.py
python3 tests/test_critic_pure.py
python3 tests/test_e2e_flow.py
python3 verify_structure.py
```
