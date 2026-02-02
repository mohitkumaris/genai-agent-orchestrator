"""
Tool Registry

Explicit tool registration with permission-based access control.
No auto-discovery - all tools must be registered explicitly.

DESIGN RULES:
- Tools are registered explicitly
- Permissions control which agents can use which tools
- Registry is the single source of truth
"""

from typing import Dict, List, Optional, Set
from mcp.tools.base import Tool


class ToolRegistry:
    """
    Central registry for all tools.
    
    Features:
    - Explicit registration (no auto-discovery)
    - Permission-based access control
    - Tool lookup by name
    """
    
    _instance: Optional["ToolRegistry"] = None
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._permissions: Dict[str, Set[str]] = {}  # tool_name -> {agent_names}
    
    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None
    
    def register(
        self,
        tool: Tool,
        allowed_agents: List[str],
    ) -> None:
        """
        Register a tool with permission restrictions.
        
        Args:
            tool: Tool instance to register
            allowed_agents: List of agent names that can use this tool
        """
        self._tools[tool.name] = tool
        self._permissions[tool.name] = set(allowed_agents)
    
    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_for_agent(self, agent_name: str) -> List[Tool]:
        """
        Get all tools available to a specific agent.
        
        Args:
            agent_name: Name of the agent requesting tools
            
        Returns:
            List of tools the agent has permission to use
        """
        available = []
        for tool_name, tool in self._tools.items():
            if agent_name in self._permissions.get(tool_name, set()):
                available.append(tool)
        return available
    
    def list_all(self) -> List[Tool]:
        """Get all registered tools."""
        return list(self._tools.values())
    
    def is_allowed(self, tool_name: str, agent_name: str) -> bool:
        """Check if an agent has permission to use a tool."""
        return agent_name in self._permissions.get(tool_name, set())


# --- Tool Registration Bootstrap ---

def bootstrap_tools() -> None:
    """
    Register default tools.
    
    Called once at startup to populate the registry.
    """
    from mcp.tools.calculator import CalculatorTool
    from mcp.tools.retrieval import RetrievalTool
    
    registry = ToolRegistry.get_instance()
    
    # Register calculator for general agent only
    registry.register(
        tool=CalculatorTool(),
        allowed_agents=["general"],
    )
    
    # Register retrieval for retrieval agent only
    registry.register(
        tool=RetrievalTool(),
        allowed_agents=["retrieval"],
    )

