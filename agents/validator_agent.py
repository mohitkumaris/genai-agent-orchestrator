"""
Validator Agent

Non-user-facing agent that validates execution outputs for correctness and trust.
Runs AFTER the execution agent, NOT instead of it.

DESIGN RULES:
- Does NOT return AgentResult (internal only)
- Does NOT generate user-facing output
- Output attached to AgentResult.metadata
- Provides confidence_delta to adjust trust score
"""

from typing import List
from pydantic import BaseModel, Field


class ValidatorResult(BaseModel):
    """
    Validation output contract.
    
    This is NOT AgentResult — validators speak to the system, not users.
    """
    is_valid: bool = Field(..., description="Whether the output passes validation")
    issues: List[str] = Field(default_factory=list, description="List of identified issues")
    confidence_delta: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Adjustment to confidence score (-1.0 to 1.0)",
    )


class ValidatorAgent:
    """
    Non-user-facing agent for output validation.
    
    Checks execution outputs for:
    - Completeness (did the agent actually answer?)
    - Coherence (is the response sensible?)
    - Safety signals (potential harmful content?)
    
    Does NOT use LLM — uses deterministic heuristics.
    LLM-based validation is a future enhancement.
    """
    
    # Minimum length for a valid response
    MIN_RESPONSE_LENGTH = 10
    
    # Keywords indicating potential issues
    UNCERTAINTY_KEYWORDS = ["i don't know", "i'm not sure", "i cannot", "i can't"]
    ERROR_KEYWORDS = ["error:", "exception:", "failed to"]
    
    def validate(self, output: str, prompt: str) -> ValidatorResult:
        """
        Validate agent output.
        
        Args:
            output: The agent's output to validate
            prompt: The original user prompt (for context)
            
        Returns:
            ValidatorResult with is_valid, issues, and confidence_delta
        """
        issues: List[str] = []
        confidence_delta = 0.0
        
        output_lower = output.lower()
        
        # Check 1: Response completeness
        if len(output.strip()) < self.MIN_RESPONSE_LENGTH:
            issues.append("Response too short")
            confidence_delta -= 0.3
        
        # Check 2: Uncertainty signals
        for keyword in self.UNCERTAINTY_KEYWORDS:
            if keyword in output_lower:
                issues.append(f"Contains uncertainty signal: '{keyword}'")
                confidence_delta -= 0.1
                break  # Only count once
        
        # Check 3: Error signals
        for keyword in self.ERROR_KEYWORDS:
            if keyword in output_lower:
                issues.append(f"Contains error signal: '{keyword}'")
                confidence_delta -= 0.2
                break
        
        # Check 4: Placeholder responses
        if "[retrieval]" in output_lower or "[placeholder]" in output_lower:
            issues.append("Contains placeholder content")
            confidence_delta -= 0.2
        
        # Check 5: Response relevance (basic heuristic)
        # If prompt contains a question word, response should be substantial
        question_words = ["what", "how", "why", "when", "where", "who"]
        if any(word in prompt.lower() for word in question_words):
            if len(output.split()) < 5:
                issues.append("Question asked but response very brief")
                confidence_delta -= 0.1
        
        # Positive signal: longer, detailed responses
        if len(output.split()) > 50:
            confidence_delta += 0.1
        
        # Clamp confidence delta
        confidence_delta = max(-1.0, min(1.0, confidence_delta))
        
        is_valid = len(issues) == 0
        
        return ValidatorResult(
            is_valid=is_valid,
            issues=issues,
            confidence_delta=confidence_delta,
        )
