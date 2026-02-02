import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Tuple

from agents.planner import ExecutionPlan, PlanStep
from agents.planner_agent import PlannerAgent, PlannerDecision
from agents.validator_agent import ValidatorAgent
from agents.analyst_agent import AnalystAgent
from agents.evaluation_agent import EvaluationAgent
from orchestration.state import ExecutionResult, StepResult, StepStatus
from schemas.request import ServiceRequest
from schemas.result import AgentResult

# Agent Imports (In production, replace with Registry)
from agents.retrieval_agent import RetrievalAgent
from agents.general_agent import GeneralAgent
from agents.critic_agent import CriticAgent

# Observability
from observability.collector import TraceCollector
from observability.sink import ConsoleTraceSink

# Evaluation Persistence
from evaluation.file_store import FileEvaluationStore

logger = logging.getLogger(__name__)

class OrchestrationExecutor:
    """
    The Engine.
    
    Orchestrates request flow:
    1. Planner decides which agent to use
    2. Selected agent executes and returns AgentResult
    3. Validator validates output (optional)
    """
    
    def __init__(
        self,
        enable_validation: bool = True,
        enable_analysis: bool = True,
        enable_evaluation: bool = True,
        enable_tracing: bool = True,
        enable_evaluation_persistence: bool = True,
    ):
        """
        Initialize the executor.
        
        Args:
            enable_validation: Whether to run validation after execution
            enable_analysis: Whether to run analysis after execution
            enable_evaluation: Whether to run quality evaluation after execution
            enable_tracing: Whether to emit execution traces
            enable_evaluation_persistence: Whether to persist evaluation data to file
        """
        # Planner for routing decisions
        self._planner = PlannerAgent()
        
        # Internal agents (non-user-facing)
        self._validator = ValidatorAgent()
        self._analyst = AnalystAgent()
        self._evaluator = EvaluationAgent()
        self._enable_validation = enable_validation
        self._enable_analysis = enable_analysis
        self._enable_evaluation = enable_evaluation
        
        # Evaluation persistence (optional)
        evaluation_store = FileEvaluationStore() if enable_evaluation_persistence else None
        
        # Tracing (observability)
        self._trace_collector = TraceCollector(
            sink=ConsoleTraceSink(verbose=True),
            enabled=enable_tracing,
            evaluation_store=evaluation_store,
        )
        
        # Service Locator for Agents
        # In a real microservice, this might look up gRPC stubs
        self.agents = {
            "retrieval": RetrievalAgent(),
            "general": GeneralAgent(),
            "critic": CriticAgent(),
        }

    def orchestrate(self, prompt: str, validate: bool = True, analyze: bool = True) -> Tuple[AgentResult, PlannerDecision]:
        """
        Full orchestration flow with planner and internal agents.
        
        Flow:
        1. Planner decides which agent should handle the prompt
        2. Selected agent is invoked
        3. Analyst analyzes output (if enabled)
        4. Validator validates output (if enabled)
        5. Evaluator scores quality (if enabled)
        6. Trace is emitted (if enabled)
        7. Returns AgentResult with analysis/validation/evaluation metadata
        
        Args:
            prompt: The user's prompt
            validate: Whether to validate the output (overrides instance setting)
            analyze: Whether to analyze the output (overrides instance setting)
            
        Returns:
            Tuple of (AgentResult, PlannerDecision)
        """
        # Tracing: capture start time and request ID
        request_id = str(uuid.uuid4())
        started_at = datetime.now()
        decision = None
        result = None
        
        try:
            # Step 1: Planner decides
            decision = self._planner.plan(prompt)
            
            # Step 2: Execute with selected agent
            result = self.execute(decision.selected_agent, prompt)
            
            # Add routing info to metadata
            result.metadata["routing"] = {
                "selected_agent": decision.selected_agent,
                "reason": decision.reason,
            }
            
            # Step 3: Analyze output (non-user-facing)
            should_analyze = self._enable_analysis and analyze
            if should_analyze:
                analysis = self._analyst.analyze(result.output, prompt)
                result.metadata["analysis"] = analysis.model_dump()
            
            # Step 4: Validate output (non-user-facing)
            should_validate = self._enable_validation and validate
            if should_validate:
                validation = self._validator.validate(result.output, prompt)
                result.metadata["validation"] = validation.model_dump()
                
                # Adjust confidence based on validation
                new_confidence = result.confidence + validation.confidence_delta
                # Clamp to [0, 1]
                result.confidence = max(0.0, min(1.0, new_confidence))
            
            # Step 5: Evaluate quality (non-user-facing)
            should_evaluate = self._enable_evaluation
            if should_evaluate:
                evaluation = self._evaluator.evaluate(result.output, prompt)
                result.metadata["evaluation"] = evaluation.model_dump()
            
            # Step 6: Emit trace (success)
            self._trace_collector.capture(
                request_id=request_id,
                result=result,
                started_at=started_at,
                success=True,
            )
            
            return result, decision
            
        except Exception as e:
            # Emit trace on failure (never swallow)
            agent_name = decision.selected_agent if decision else "unknown"
            self._trace_collector.capture_failure(
                request_id=request_id,
                agent_name=agent_name,
                started_at=started_at,
                error=str(e),
                metadata=result.metadata if result else {},
            )
            raise  # Re-raise - never swallow exceptions

    def execute(self, agent_name: str, prompt: str) -> AgentResult:
        """
        Simple execution path: route to agent and return structured result.
        
        Returns AgentResult with confidence and metadata.
        
        Args:
            agent_name: Name of the agent to invoke (e.g., 'general', 'retrieval')
            prompt: The user's prompt
            
        Returns:
            AgentResult: Canonical agent result with agent_name, output, confidence, metadata
        """
        agent = self.agents.get(agent_name)
        if not agent:
            return AgentResult(
                agent_name=agent_name,
                output=f"Error: No agent found for '{agent_name}'",
                confidence=0.0,
                metadata={"error": "agent_not_found"},
            )
        
        # Agent.run() now returns AgentResult directly
        return agent.run(prompt)
        
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
