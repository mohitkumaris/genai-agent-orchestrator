"""
Calculator Tool

Simple arithmetic calculator for demonstration.
Returns structured data, not user-facing strings.
"""

import re
from typing import Any, Dict
from mcp.tools.base import Tool, ToolResult


class CalculatorTool(Tool):
    """
    Basic arithmetic calculator.
    
    Supports: +, -, *, /, parentheses
    Returns structured result with expression and answer.
    """
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return "Perform basic arithmetic calculations. Input: mathematical expression string."
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (e.g., '2 + 3 * 4')",
                }
            },
            "required": ["expression"],
        }
    
    def run(self, input: Dict[str, Any]) -> ToolResult:
        """
        Evaluate arithmetic expression.
        
        Args:
            input: {"expression": "2 + 3 * 4"}
            
        Returns:
            ToolResult with {"result": 14, "expression": "2 + 3 * 4"}
        """
        expression = input.get("expression", "")
        
        if not expression:
            return ToolResult.fail("Missing 'expression' in input")
        
        try:
            # Sanitize: only allow numbers, operators, parentheses, spaces
            sanitized = re.sub(r"[^0-9+\-*/().\s]", "", expression)
            
            if not sanitized.strip():
                return ToolResult.fail(f"Invalid expression: {expression}")
            
            # Evaluate safely
            result = eval(sanitized, {"__builtins__": {}}, {})
            
            return ToolResult.ok({
                "result": result,
                "expression": expression,
            })
            
        except ZeroDivisionError:
            return ToolResult.fail("Division by zero")
        except Exception as e:
            return ToolResult.fail(f"Calculation error: {str(e)}")
