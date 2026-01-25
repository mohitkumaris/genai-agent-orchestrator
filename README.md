# genai-agent-orchestrator

The cognitive core of the GenAI Platform. This service is responsible for:
- Accepting user requests
- Planning execution strategies (PlannerAgent)
- Routing to specialized agents
- Orchestrating multi-step reasoning (OrchestrationExecutor)
- Invoking tools via MCP (Model Context Protocol)

## Architecture

This service follows a **Strict Flat Layout** (No `src/`) and uses **FastAPI** + **LangChain**.

### Layers
- **app/**: API Gateway (FastAPI). No business logic.
- **orchestration/**: The "Brain". `Executor` runs immutable `ExecutionPlans`.
- **agents/**: Stateless specialists (`Planner`, `Retrieval`).
- **mcp_client/**: Protocol layer for tool invocation.
- **schemas/**: Domain models (`Plan`, `Result`).

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
python3 verify_structure.py
```
