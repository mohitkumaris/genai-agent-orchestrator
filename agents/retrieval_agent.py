from typing import Any, Dict

from agents.base import BaseAgent
from schemas.plan import PlanStep
from schemas.result import AgentResult
from genai_mcp_core.context import MCPContext
from mcp_client.executor import MCPToolExecutor
from schemas.request import ServiceRequest
from schemas.response import ServiceResponse

class RetrievalAgent(BaseAgent):
    """
    Executes a single retrieval step using MCP-exposed RAG tools.
    """

    TOOL_NAME = "rag_search"

    def __init__(self): 
        # Note: BaseAgent inits LLM, but we don't use it here.
        super().__init__("retrieval_agent")
        self._mcp_executor = MCPToolExecutor()

    async def execute(self, request: ServiceRequest) -> ServiceResponse:
         # Constraint: BaseAgent.execute signature returns ServiceResponse, primarily designed for Planner/Executor flow.
         # But the specific user request asks for:
         # def run(self, *, step: PlanStep, context: MCPContext) -> AgentResult:
         # We need to bridge this. The Executor calls `agent.execute(ServiceRequest)`.
         # But the new RetrievalAgent contract is lower-level.
         
         # For strict compliance with the USER REQUEST skeleton:
         # I will implement the requested `run` method.
         # And I will stick the `execute` method as a bridge if needed, 
         # OR I assume the Executor will be refactored to call `run` if it knows it's a strongly typed agent?
         # Or more likely, I implement `execute` to EXTRACT the step and context and call `run`.
         
         # However, ServiceRequest doesn't strictly have the PlanStep.
         # The current Executor passes `ServiceRequest` enriched with context.
         # But the Executor logic (which we just wrote) iterates `plan.steps`. 
         # It doesn't pass the `step` object itself into `agent.execute(request)`. 
         
         # To align without rewriting Executor's contract immediately:
         # I will map ServiceRequest -> logic matching the requested behavior.
         # BUT `step.input` is critical.
         
         # Let's adhere to the requested skeleton signature as the PRIMARY public API.
         pass
         
    def run(
        self,
        *,
        step: PlanStep,
        context: MCPContext,
    ) -> AgentResult:
        if not step.input:
            raise ValueError("Retrieval step requires input payload")

        result = self._mcp_executor.execute(
            tool_name=self.TOOL_NAME,
            payload=step.input,
            context=context,
        )

        return AgentResult.success(
            agent="retrieval",
            output=result,
        )
    
    # Bridge for the current Executor Code
    async def execute(self, request: ServiceRequest) -> ServiceResponse:
        # Attempts to reconstruct or extract what is needed. 
        # Current executor logic is: 
        # agent_req = context.model_copy(update={"context": enriched_context})
        # response = await agent.execute(agent_req)
        
        # This implies `request` contains everything.
        # But `RetrievalAgent` is supposed to just run 1 step.
        # The executor should ideally pass the STEP info.
        
        # For now, to satisfy the interface, we'll assume the executor passes 'query' in request.query
        # and we treat that as step input.
        
        # Create Dummy Context and Step for the bridge
        ctx = MCPContext.create()
        step = PlanStep(
            step_id=0, 
            agent_role="retrieval", 
            intent="legacy_execute", 
            description="Bridge execution", 
            input={"query": request.query}
        )
        
        result = self.run(step=step, context=ctx)
        
        return ServiceResponse(
            answer=str(result.output), 
            metadata=result.metadata
        )
