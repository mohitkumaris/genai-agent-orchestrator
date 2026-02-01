"""
FastAPI Dependencies

All object creation happens here, not per request.
This module provides dependency injection for the orchestration layer.

RULE: FastAPI routes call exactly one entry point — OrchestrationRouter.handle()
"""

from functools import lru_cache

from agents.planner import PlannerAgent
from agents.critic_agent import CriticAgent
from orchestration.executor import OrchestrationExecutor
from orchestration.router import OrchestrationRouter


@lru_cache(maxsize=1)
def get_orchestration_router() -> OrchestrationRouter:
    """
    Create and cache the OrchestrationRouter singleton.
    
    All components are wired here:
    - PlannerAgent: Creates immutable execution plans
    - OrchestrationExecutor: Runs plans step-by-step
    - CriticAgent: Validates outputs before user exposure
    
    Returns:
        OrchestrationRouter: The single entry point for orchestration.
    """
    planner = PlannerAgent()
    executor = OrchestrationExecutor()
    critic = CriticAgent()
    
    return OrchestrationRouter(
        planner=planner,
        executor=executor,
        critic=critic,
    )
