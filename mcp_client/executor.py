from typing import Any, Callable, Dict, List, Optional
from langchain_core.tools import StructuredTool # type: ignore
from pydantic import create_model # type: ignore

from genai_mcp_core.tool import ToolDefinition
from genai_mcp_core.context import MCPContext
from genai_mcp_core.handler import ToolSuccess, ToolFailure

class MCPToolExecutor:
    """
    Exposes remote execution of tools via MCP.
    """
    def __init__(self, tool_def: Optional[ToolDefinition] = None):
        self.tool_def = tool_def
    
    def execute(self, tool_name: Optional[str] = None, payload: Dict[str, Any] = None, **kwargs: Any) -> Any:
        """
        Execute a tool.
        Can be called via LangChain style (**kwargs) or Direct Style (tool_name, payload).
        """
        name = tool_name or (self.tool_def.name if self.tool_def else "unknown")
        data = payload if payload is not None else kwargs 
        
        # Mock Execution Logic - In real world, this sends HTTP request to the named tool
        if name == "rag_search":
            query = data.get("query", "unknown")
            return [
                {"content": f"Mock retrieved content for '{query}'", "score": 0.9, "source": "doc_1"},
                {"content": f"Secondary content for '{query}'", "score": 0.85, "source": "doc_2"}
            ]
            
        return f"Executed {name} with {data}"

def adapt_to_langchain(tool_def: ToolDefinition) -> StructuredTool:
    """
    Converts MCP Definition to LangChain Tool.
    """
    executor = MCPToolExecutor(tool_def)
    
    # Dynamic Pydantic Model for Arguments
    fields = {}
    for name, schema in tool_def.input_schema.get("properties", {}).items():
        # Simplistic mapping
        fields[name] = (Any, ...)
        
    args_schema = create_model(f"{tool_def.name}_Input", **fields) # type: ignore
    
    return StructuredTool.from_function(
        func=executor.execute,
        name=tool_def.name,
        description=tool_def.description,
        args_schema=args_schema
    )
