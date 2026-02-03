"""
General Agent

General-purpose agent for handling user queries.
Uses LangChain internally via the langchain_adapter.

DESIGN RULE: LangChain is encapsulated - only execution agents use it.
TOOL RULE: Tools are optional, opt-in per agent, and tracked in metadata.
"""

from typing import List
from agents.base import BaseAgent
from schemas.request import ServiceRequest
from schemas.response import ServiceResponse
from schemas.result import AgentResult
from llm.langchain_adapter import generate, generate_with_tools


class GeneralAgent(BaseAgent):
    """
    General-purpose agent for handling user queries.
    
    Returns AgentResult with confidence and metadata.
    Uses LangChain internally (via adapter).
    Optionally uses tools when enabled.
    """
    
    AGENT_NAME = "general"
    DEFAULT_CONFIDENCE = 0.6  # Static confidence for now
    
    # System prompt for general queries
    SYSTEM_PROMPT = """You are a helpful AI assistant. Provide clear, accurate, and concise answers to user questions.

When you need to perform calculations, use the calculator tool instead of computing manually."""
    
    def __init__(self, enable_tools: bool = False):
        """
        Initialize the GeneralAgent.
        
        Args:
            enable_tools: If True, load tools from registry for this agent.
                         Default is False to preserve existing behavior.
        """
        super().__init__("general_agent")
        self._enable_tools = enable_tools
        self._tools: List = []
        
        if enable_tools:
            from mcp.tools.registry import ToolRegistry
            self._tools = ToolRegistry.get_instance().list_for_agent(self.AGENT_NAME)
    
    async def execute(self, request: ServiceRequest) -> ServiceResponse:
        """
        Full request context execution (async).
        
        Legacy method for backward compatibility.
        """
        if self._tools:
            output, _ = generate_with_tools(request.query, self._tools, system_prompt=self.SYSTEM_PROMPT)
        else:
            output, _ = generate(request.query, system_prompt=self.SYSTEM_PROMPT)
        return ServiceResponse(answer=output)

    def run(self, prompt: str, context_str: str = "") -> AgentResult:
        """
        Simple synchronous interface for agent execution.
        
        Args:
            prompt: User query
            context_str: Optional conversation context to inject
            
        Returns AgentResult with output, confidence, and metadata.
        Uses LangChain adapter internally - no LangChain types leak out.
        Tool usage is tracked in metadata["tool_calls"].
        """
        # Inject context if provided
        final_prompt = f"{context_str}\n\n{prompt}" if context_str else prompt
        
        if self._tools:
            output, metadata = generate_with_tools(final_prompt, self._tools, system_prompt=self.SYSTEM_PROMPT)
        else:
            output, metadata = generate(final_prompt, system_prompt=self.SYSTEM_PROMPT)
        
        return AgentResult(
            agent_name=self.AGENT_NAME,
            output=output,
            confidence=self.DEFAULT_CONFIDENCE,
            metadata=metadata,
        )

