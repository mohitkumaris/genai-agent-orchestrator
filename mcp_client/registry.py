from typing import Any, Dict, List
from genai_mcp_core.tool import ToolDefinition

# In a real system, this would load from a centralized registry service or config.
# Here we define the tool contracts we expect to exist in the platform.

RAG_SEARCH_TOOL = ToolDefinition(
    name="rag_search",
    description="Search the RAG system for relevant document chunks.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "top_k": {"type": "integer", "default": 5}
        },
        "required": ["query"]
    },
    output_schema={
        "type": "object", 
        "properties": {
            "results": {"type": "array"}
        }
    }
)

ALL_TOOLS: List[ToolDefinition] = [
    RAG_SEARCH_TOOL
]

def get_tools_for_agent(agent_name: str) -> List[ToolDefinition]:
    """Return tools authorized for a given agent."""
    if agent_name == "retrieval_agent":
        return [RAG_SEARCH_TOOL]
    return []
