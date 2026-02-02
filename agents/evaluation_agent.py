"""
Evaluation Agent

Non-user-facing agent that provides quality scoring and feedback signals.
Runs AFTER execution for observability and future learning.

DESIGN RULES:
- Does NOT return AgentResult (internal only)
- Does NOT generate user-facing output
- Output attached to AgentResult.metadata
- Provides quality signals for evals and future optimization
"""

from typing import Dict
from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    """
    Evaluation output contract.
    
    This is NOT AgentResult — evaluators speak to the system, not users.
    """
    score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Overall quality score (0=poor, 1=excellent)",
    )
    signals: Dict[str, float] = Field(
        default_factory=dict,
        description="Individual quality signals (each 0-1)",
    )


class EvaluationAgent:
    """
    Non-user-facing agent for quality evaluation.
    
    Evaluates execution outputs to provide:
    - Overall quality score
    - Individual quality signals (accuracy, clarity, completeness, etc.)
    
    Does NOT use LLM — uses deterministic heuristics.
    LLM-based evaluation is a future enhancement.
    """
    
    def evaluate(self, output: str, prompt: str) -> EvaluationResult:
        """
        Evaluate agent output quality.
        
        Args:
            output: The agent's output
            prompt: The original user prompt
            
        Returns:
            EvaluationResult with score and signals
        """
        signals: Dict[str, float] = {}
        
        # Signal 1: Completeness (did the response address the prompt?)
        signals["completeness"] = self._score_completeness(output, prompt)
        
        # Signal 2: Clarity (readability heuristics)
        signals["clarity"] = self._score_clarity(output)
        
        # Signal 3: Conciseness (not too verbose, not too brief)
        signals["conciseness"] = self._score_conciseness(output, prompt)
        
        # Signal 4: Confidence (self-assuredness of response)
        signals["response_confidence"] = self._score_response_confidence(output)
        
        # Overall score: weighted average of signals
        weights = {
            "completeness": 0.35,
            "clarity": 0.25,
            "conciseness": 0.20,
            "response_confidence": 0.20,
        }
        
        overall_score = sum(
            signals[key] * weights.get(key, 0.25)
            for key in signals
        )
        
        return EvaluationResult(
            score=min(1.0, max(0.0, overall_score)),
            signals=signals,
        )
    
    def _score_completeness(self, output: str, prompt: str) -> float:
        """Score how complete the response is relative to the prompt."""
        score = 0.5  # Base score
        
        # Longer responses for complex prompts = more complete
        prompt_words = len(prompt.split())
        output_words = len(output.split())
        
        if prompt_words > 10 and output_words > 30:
            score += 0.3
        elif output_words > 10:
            score += 0.2
        
        # Questions in prompt should have substantial answers
        if "?" in prompt and output_words > 5:
            score += 0.1
        
        # Penalize very short responses for any meaningful prompt
        if output_words < 5 and prompt_words > 3:
            score -= 0.3
        
        return min(1.0, max(0.0, score))
    
    def _score_clarity(self, output: str) -> float:
        """Score clarity and readability."""
        score = 0.7  # Base score
        
        # Structured content = clearer
        if any(marker in output for marker in ["1.", "2.", "•", "-", ":", "\n"]):
            score += 0.2
        
        # Very long sentences = less clear
        sentences = output.split(".")
        avg_sentence_words = sum(len(s.split()) for s in sentences) / max(1, len(sentences))
        if avg_sentence_words > 30:
            score -= 0.2
        
        return min(1.0, max(0.0, score))
    
    def _score_conciseness(self, output: str, prompt: str) -> float:
        """Score conciseness (not too verbose, not too brief)."""
        prompt_words = len(prompt.split())
        output_words = len(output.split())
        
        # Ideal ratio depends on prompt type
        # For simple questions, brief is good
        # For complex prompts, more detail is acceptable
        
        if prompt_words < 10:
            # Simple prompt: brief responses are good
            if 5 <= output_words <= 50:
                return 0.9
            elif output_words < 5:
                return 0.5
            else:
                return 0.7
        else:
            # Complex prompt: more detail is acceptable
            if 20 <= output_words <= 150:
                return 0.9
            elif output_words < 20:
                return 0.6
            else:
                return 0.7
    
    def _score_response_confidence(self, output: str) -> float:
        """Score how confident the response appears."""
        output_lower = output.lower()
        score = 0.8  # Base score
        
        # Uncertainty markers reduce confidence score
        uncertainty_phrases = [
            "i think", "maybe", "perhaps", "possibly",
            "i'm not sure", "i don't know", "it could be",
        ]
        
        for phrase in uncertainty_phrases:
            if phrase in output_lower:
                score -= 0.1
        
        # Definitive language increases score
        confident_phrases = ["is", "are", "equals", "the answer is"]
        for phrase in confident_phrases:
            if phrase in output_lower:
                score += 0.05
                break
        
        return min(1.0, max(0.0, score))
