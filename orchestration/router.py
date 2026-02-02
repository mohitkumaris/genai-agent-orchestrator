"""
Orchestration Router

The single-direction flow controller for the GenAI platform.

FLOW GUARANTEES (NON-NEGOTIABLE):
1. Planner runs EXACTLY ONCE
2. ExecutionPlan is IMMUTABLE
3. Executor NEVER modifies the plan
4. Agents do NOT call each other
5. Critic runs AFTER execution (not during)
6. No back-edges, no re-planning

FLOW:
Request → Planner → ExecutionPlan → Executor → Critic → FinalResponse
"""

import uuid
import logging
from typing import Optional

from agents.planner import PlannerAgent
from agents.critic_agent import CriticAgent
from orchestration.executor import OrchestrationExecutor
from schemas.request import ServiceRequest
from schemas.response import FinalResponse
from genai_mcp_core.context import MCPContext


logger = logging.getLogger(__name__)


class OrchestrationRouter:
    """
    Entry point for executing a full GenAI request.
    
    This is the glue, not the brain. It coordinates components
    but contains zero business logic.
    
    GUARANTEES:
    - Planner runs exactly once
    - Executor never modifies the plan
    - Critic runs after execution (not during)
    - No back-edges, no re-planning
    """

    def __init__(
        self,
        planner: Optional[PlannerAgent] = None,
        executor: Optional[OrchestrationExecutor] = None,
        critic: Optional[CriticAgent] = None,
    ):
        """
        Initialize the router with injected dependencies.
        
        Args:
            planner: The planning agent (creates immutable plans)
            executor: The execution engine (runs plans step-by-step)
            critic: The validation agent (evaluates final output)
        """
        self._planner = planner or PlannerAgent()
        self._executor = executor or OrchestrationExecutor()
        self._critic = critic or CriticAgent()

    async def handle(
        self,
        *,
        request: ServiceRequest,
        context: Optional[MCPContext] = None,
    ) -> FinalResponse:
        """
        Execute the complete orchestration flow.
        
        Args:
            request: Validated user request
            context: MCP context (created if not provided)
            
        Returns:
            FinalResponse: Structured response with payload and metadata
        """
        trace_id = request.trace_id or str(uuid.uuid4())
        mcp_context = context or MCPContext.create()
        
        logger.info(f"[{trace_id}] Starting orchestration flow")
        
        # =====================================================
        # STEP 1: PLANNING (runs exactly once)
        # =====================================================
        logger.info(f"[{trace_id}] Phase 1: Planning")
        plan = await self._planner.plan(request)
        logger.info(f"[{trace_id}] Plan created: {plan.plan_id} ({len(plan.steps)} steps)")
        
        # Plan is now IMMUTABLE — no modifications allowed
        
        # =====================================================
        # STEP 2: EXECUTION (deterministic, step-by-step)
        # =====================================================
        logger.info(f"[{trace_id}] Phase 2: Execution")
        execution_result = await self._executor.execute_plan(plan, request)
        logger.info(f"[{trace_id}] Execution complete: status={execution_result.status}")
        
        # =====================================================
        # STEP 3: VALIDATION (post-execution only)
        # =====================================================
        logger.info(f"[{trace_id}] Phase 3: Validation")
        critic_result = self._critic.validate_from_execution(execution_result)
        logger.info(f"[{trace_id}] Validation complete: {critic_result.recommendation}")
        
        # =====================================================
        # STEP 4: ASSEMBLY (structured output)
        # =====================================================
        logger.info(f"[{trace_id}] Phase 4: Response Assembly")
        final_response = FinalResponse.from_execution(
            execution_result=execution_result,
            critic_result=critic_result,
            trace_id=trace_id,
        )
        
        logger.info(f"[{trace_id}] Flow complete: is_safe={final_response.is_safe}")
        
        return final_response


