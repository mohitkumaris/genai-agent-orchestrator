"""
Tool Base Interface

Canonical Tool contract for MCP-style tool abstraction.
Tools return structured output, never user-facing strings.

CAPABILITY BOUNDARY (NON-NEGOTIABLE):
    API ❌
    Orchestrator ❌
    Planner ❌
    Internal Agents ❌
    Execution Agents ✅  ← tools live ONLY here
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """
    Structured result from tool execution.
    
    Tools return data, NOT user-facing strings.
    This output is attached to AgentResult.metadata.
    """
    output: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured output from the tool",
    )
    success: bool = Field(
        default=True,
        description="Whether the tool executed successfully",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if execution failed",
    )
    
    @classmethod
    def ok(cls, output: Dict[str, Any]) -> "ToolResult":
        """Factory for successful results."""
        return cls(output=output, success=True)
    
    @classmethod
    def fail(cls, error: str) -> "ToolResult":
        """Factory for failed results."""
        return cls(output={}, success=False, error=error)


class Tool(ABC):
    """
    Abstract base class for all tools.
    
    Tools:
    - Return structured output (dict)
    - Never return user-facing strings
    - Attach output to metadata
    
    Implement `run()` to define tool behavior.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for LLM context."""
        pass
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        """
        JSON Schema for tool input validation.
        
        Override to define required parameters.
        Default: accepts any dict.
        """
        return {"type": "object", "properties": {}}
    
    @abstractmethod
    def run(self, input: Dict[str, Any]) -> ToolResult:
        """
        Execute the tool with given input.
        
        Args:
            input: Dictionary matching input_schema
            
        Returns:
            ToolResult with structured output
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize tool definition for registration/display."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
