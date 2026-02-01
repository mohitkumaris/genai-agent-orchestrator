import logging
import time
import uuid
from typing import Dict, Any, List

from agents.planner import ExecutionPlan, PlanStep
from orchestration.state import ExecutionResult, StepResult, StepStatus
from schemas.request import ServiceRequest
from schemas.result import OrchestrationResult

# Agent Imports (In production, replace with Registry)
from agents.retrieval_agent import RetrievalAgent
from agents.general_agent import GeneralAgent
from agents.critic_agent import CriticAgent
# from agents.planner import PlannerAgent # Planner is not used here, only Plan object

logger = logging.getLogger(__name__)

class OrchestrationExecutor:
    """
    The Engine.
    Executes a static ExecutionPlan step-by-step.
    """
    
    def __init__(self):
        # Service Locator for Agents
        # In a real microservice, this might look up gRPC stubs
        self.agents = {
            "retrieval": RetrievalAgent(),
            "general": GeneralAgent(),
            "critic": CriticAgent(),
            # "analytics": AnalyticsAgent(),
        }

    def execute(self, agent_name: str, prompt: str) -> OrchestrationResult:
        """
        Simple execution path: route to agent and return typed result.
        
        This is the minimal typed interface for agent invocation.
        
        Args:
            agent_name: Name of the agent to invoke (e.g., 'general', 'retrieval')
            prompt: The user's prompt
            
        Returns:
            OrchestrationResult: Typed result with agent_name and output
        """
        agent = self.agents.get(agent_name)
        if not agent:
            return OrchestrationResult(
                agent_name=agent_name,
                output=f"Error: No agent found for '{agent_name}'"
            )
        
        output = agent.run(prompt)
        return OrchestrationResult(agent_name=agent_name, output=output)
        
    async def execute_plan(self, plan: ExecutionPlan, context: ServiceRequest) -> ExecutionResult:
        """
        Execute the provided plan.
        
        Args:
            plan: The immutable play to execute.
            context: Original user request and metadata.
            
        Returns:
            ExecutionResult: Structured output.
        """
        plan_id = plan.plan_id
        logger.info(f"Starting execution of Plan ID: {plan_id} (Type: {plan.task_type})")
        
        results = []
        final_output = None
        global_status = StepStatus.RUNNING
        
        try:
            for step in plan.steps:
                logger.info(f"Executing Step {step.step_id}: {step.intent} (Agent: {step.agent_role})")
                
                step_result = await self._execute_step(step, context, results)
                results.append(step_result)
                
                if step_result.status == StepStatus.FAILED:
                    logger.error(f"Step {step.step_id} failed. Aborting.")
                    global_status = StepStatus.FAILED
                    break
            
            if global_status != StepStatus.FAILED:
                global_status = StepStatus.COMPLETED
                # Synthesize final output from last step (simplification)
                if results:
                    final_output = str(results[-1].output)
                else:
                    final_output = "No steps executed."
                    
        except Exception as e:
            logger.exception("Critical execution error")
            global_status = StepStatus.FAILED
            final_output = f"Execution crashed: {str(e)}"
            
        return ExecutionResult(
            plan_id=plan_id,
            status=global_status,
            step_results=results,
            final_output=final_output,
            execution_trace={
                "task_type": plan.task_type,
                "complexity": plan.estimated_complexity,
                "timestamp": time.time()
            }
        )

    async def _execute_step(self, step: PlanStep, context: ServiceRequest, previous_results: List[StepResult]) -> StepResult:
        """
        Execute a single step.
        """
        start_time = time.time()
        agent = self.agents.get(step.agent_role)
        
        # Mapping generic roles to implemented agents if mismatch
        if not agent and step.agent_role == "retrieval_agent": agent = self.agents.get("retrieval")
        if not agent and step.agent_role == "general_agent": agent = self.agents.get("general")

        if not agent:
             return StepResult(
                step_id=step.step_id,
                agent_role=step.agent_role,
                status=StepStatus.FAILED,
                error=f"No agent found for role: {step.agent_role}",
                metadata={"intent": step.intent}
            )

        try:
            # Prepare Request for Agent
            # Agents expect ServiceRequest. 
            # We might need to enrich it with context from previous steps.
            # For v1, we just pass the original query + previous context?
            # Actually, agents might need the *output* of previous steps.
            # Let's append previous outputs to conversation history or context.
            
            enriched_context = context.context.copy()
            for prev in previous_results:
                enriched_context[f"step_{prev.step_id}_output"] = prev.output
                
            # TODO: If step description implies a specific sub-query, we might need to modify query
            # For now, pass original query.
            
            agent_req = context.model_copy(update={"context": enriched_context})
            
            # Execute
            response = await agent.execute(agent_req)
            
            duration = (time.time() - start_time) * 1000
            
            return StepResult(
                step_id=step.step_id,
                agent_role=step.agent_role,
                status=StepStatus.COMPLETED,
                output=response.answer, # Extracting answer
                duration_ms=duration,
                metadata=response.metadata
            )
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return StepResult(
                step_id=step.step_id,
                agent_role=step.agent_role,
                status=StepStatus.FAILED,
                error=str(e),
                duration_ms=duration
            )
