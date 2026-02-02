"""
Retrieval Agent

Execution agent for RAG (Retrieval-Augmented Generation).
Uses retrieval tool to get documents, then LLM to generate grounded response.

DESIGN RULES:
- Retrieval is a TOOL, not orchestration logic
- Tool usage tracked in metadata
- Documents never exposed raw to API
- LLM generates final response grounded in context
"""

from typing import List
from agents.base import BaseAgent
from schemas.request import ServiceRequest
from schemas.response import ServiceResponse
from schemas.result import AgentResult
from llm.langchain_adapter import generate_with_context


class RetrievalAgent(BaseAgent):
    """
    RAG agent using tool + LLM pattern.
    
    Flow:
    1. Call retrieval tool to get relevant documents
    2. Pass documents as context to LLM
    3. Return grounded response with documents in metadata
    """
    
    AGENT_NAME = "retrieval"
    DEFAULT_CONFIDENCE = 0.7  # Higher confidence due to grounding
    
    def __init__(self, enable_tools: bool = True):
        """
        Initialize the RetrievalAgent.
        
        Args:
            enable_tools: If True (default), use retrieval tool.
                         If False, falls back to simulated retrieval.
        """
        super().__init__("retrieval_agent")
        self._enable_tools = enable_tools
        self._retrieval_tool = None
        
        if enable_tools:
            from mcp.tools.registry import ToolRegistry
            tools = ToolRegistry.get_instance().list_for_agent(self.AGENT_NAME)
            # Find retrieval tool
            for tool in tools:
                if tool.name == "retrieval":
                    self._retrieval_tool = tool
                    break
    
    async def execute(self, request: ServiceRequest) -> ServiceResponse:
        """
        Full request context execution (async).
        
        Bridge for OrchestrationExecutor compatibility.
        """
        result = self.run(request.query)
        return ServiceResponse(
            answer=result.output,
            metadata=result.metadata,
        )
    
    def run(self, prompt: str) -> AgentResult:
        """
        Execute RAG: retrieval tool → LLM with context.
        
        Returns AgentResult with:
        - output: LLM-generated response grounded in context
        - metadata: includes retrieval info (documents, scores)
        """
        if not self._retrieval_tool:
            return self._run_fallback(prompt)
        
        # Step 1: Call retrieval tool
        retrieval_result = self._retrieval_tool.run({
            "query": prompt,
            "k": 3,
        })
        
        if not retrieval_result.success:
            return AgentResult(
                agent_name=self.AGENT_NAME,
                output=f"Retrieval failed: {retrieval_result.error}",
                confidence=0.1,
                metadata={"error": retrieval_result.error},
            )
        
        documents = retrieval_result.output.get("documents", [])
        
        if not documents:
            return AgentResult(
                agent_name=self.AGENT_NAME,
                output="No relevant documents found for your query.",
                confidence=0.3,
                metadata={"retrieval": {"documents": [], "query": prompt}},
            )
        
        # Step 2: Generate with context
        output, metadata = generate_with_context(
            prompt=prompt,
            context_documents=documents,
        )
        
        # Step 3: Enrich metadata with retrieval info
        metadata["retrieval"] = {
            "documents": documents,
            "query": retrieval_result.output.get("query", prompt),
            "total_retrieved": retrieval_result.output.get("total_retrieved", len(documents)),
        }
        
        return AgentResult(
            agent_name=self.AGENT_NAME,
            output=output,
            confidence=self.DEFAULT_CONFIDENCE,
            metadata=metadata,
        )
    
    def _run_fallback(self, prompt: str) -> AgentResult:
        """Fallback when tools are disabled."""
        from llm.langchain_adapter import generate
        
        system_prompt = """You are a retrieval assistant. When asked to search or find information, 
provide a helpful response. Note that retrieval tools are currently disabled."""
        
        output, metadata = generate(prompt, system_prompt=system_prompt)
        metadata["note"] = "Retrieval tools disabled - using direct LLM"
        
        return AgentResult(
            agent_name=self.AGENT_NAME,
            output=output,
            confidence=0.4,
            metadata=metadata,
        )
