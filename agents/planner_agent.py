"""
Planner Agent

Control plane agent that decides which agent should handle a request.
Does NOT execute the request, call LLMs, or produce user-facing output.

DESIGN RULES:
- Planner is control logic, NOT intelligence
- Returns routing decision, NOT AgentResult
- Uses deterministic heuristics, NOT Azure OpenAI
- Defaults to 'general' agent
- NO policy logic (policy lives in orchestration layer)
"""

from typing import Optional
from pydantic import BaseModel, Field


class PlannerDecision(BaseModel):
    """
    Routing decision from the planner.
    
    This is the ONLY output format the planner produces.
    No AgentResult, no user-facing content.
    """
    selected_agent: str = Field(..., description="Name of the agent to handle this request")
    reason: str = Field(..., description="Brief explanation for the routing decision")


class PlannerAgent:
    """
    Planner Agent for routing decisions.
    
    Inspects user prompt and decides which agent should handle it.
    Uses simple deterministic logic - NOT an LLM.
    
    NOTE: This agent has NO policy awareness.
          Policy influence is computed in orchestration layer.
    
    Flow:
        User Prompt → PlannerAgent → { selected_agent, reason } → Orchestration
    """
    
    # Available agents for routing
    AVAILABLE_AGENTS = ["general", "retrieval", "critic"]
    DEFAULT_AGENT = "general"
    
    def plan(self, prompt: str) -> PlannerDecision:
        """
        Decide which agent should handle this prompt.
        
        Args:
            prompt: The user's prompt
            
        Returns:
            PlannerDecision with selected_agent and reason
        """
        # SAFE GUARD: Handle empty or invalid input
        if not prompt or not isinstance(prompt, str) or not prompt.strip():
             return PlannerDecision(
                selected_agent=self.DEFAULT_AGENT,
                reason="Default routing for general queries",
            )

        try:
            prompt_lower = prompt.lower()
            
            # Simple deterministic heuristics (scaffolding, not final intelligence)
            if any(keyword in prompt_lower for keyword in ["search", "find", "lookup", "retrieve", "document"]):
                return PlannerDecision(
                    selected_agent="retrieval",
                    reason="Contains retrieval-related keywords",
                )
            
            if any(keyword in prompt_lower for keyword in ["validate", "verify", "check", "review", "critique"]):
                return PlannerDecision(
                    selected_agent="critic",
                    reason="Contains validation-related keywords",
                )
            
            # Default to general agent for all other cases
            return PlannerDecision(
                selected_agent=self.DEFAULT_AGENT,
                reason="Default routing for general queries",
            )
        except Exception:
            # Fallback for any internal error
            return PlannerDecision(
                selected_agent=self.DEFAULT_AGENT,
                reason="Default routing for general queries",
            )
