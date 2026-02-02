"""
Analyst Agent

Non-user-facing agent that provides reasoning decomposition.
Runs AFTER the execution agent for observability, NOT to generate output.

DESIGN RULES:
- Does NOT return AgentResult (internal only)
- Does NOT generate user-facing output
- Output attached to AgentResult.metadata
- Provides analysis_steps for debugging and evals
"""

from typing import List
from pydantic import BaseModel, Field


class AnalystResult(BaseModel):
    """
    Analysis output contract.
    
    This is NOT AgentResult — analysts speak to the system, not users.
    """
    analysis_steps: List[str] = Field(
        default_factory=list,
        description="Reasoning steps identified in the output",
    )
    complexity_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Estimated complexity of the task (0=simple, 1=complex)",
    )
    query_type: str = Field(
        default="general",
        description="Classified query type (e.g., 'factual', 'reasoning', 'creative')",
    )


class AnalystAgent:
    """
    Non-user-facing agent for reasoning analysis.
    
    Analyzes both prompt and output to provide:
    - Reasoning steps breakdown
    - Query type classification
    - Complexity estimation
    
    Does NOT use LLM — uses deterministic heuristics.
    LLM-based analysis is a future enhancement.
    """
    
    # Query type keywords
    FACTUAL_KEYWORDS = ["what is", "who is", "when", "where", "define", "explain"]
    REASONING_KEYWORDS = ["why", "how does", "compare", "analyze", "evaluate"]
    CREATIVE_KEYWORDS = ["write", "create", "generate", "imagine", "story"]
    CALCULATION_KEYWORDS = ["calculate", "compute", "how much", "how many", "+", "-", "*", "/"]
    
    def analyze(self, output: str, prompt: str) -> AnalystResult:
        """
        Analyze agent output and prompt.
        
        Args:
            output: The agent's output
            prompt: The original user prompt
            
        Returns:
            AnalystResult with analysis_steps, complexity_score, query_type
        """
        analysis_steps: List[str] = []
        prompt_lower = prompt.lower()
        output_lower = output.lower()
        
        # Step 1: Classify query type
        query_type = self._classify_query(prompt_lower)
        analysis_steps.append(f"Query classified as: {query_type}")
        
        # Step 2: Estimate complexity
        complexity_score = self._estimate_complexity(prompt, output)
        analysis_steps.append(f"Complexity estimated: {complexity_score:.2f}")
        
        # Step 3: Identify key elements
        word_count = len(output.split())
        analysis_steps.append(f"Response contains {word_count} words")
        
        # Step 4: Check for structured content
        if any(marker in output for marker in ["1.", "2.", "•", "-", "*"]):
            analysis_steps.append("Response contains structured/list content")
        
        # Step 5: Check for code
        if "```" in output or "def " in output_lower or "function" in output_lower:
            analysis_steps.append("Response contains code elements")
        
        return AnalystResult(
            analysis_steps=analysis_steps,
            complexity_score=complexity_score,
            query_type=query_type,
        )
    
    def _classify_query(self, prompt_lower: str) -> str:
        """Classify the query type based on keywords."""
        if any(kw in prompt_lower for kw in self.CALCULATION_KEYWORDS):
            return "calculation"
        if any(kw in prompt_lower for kw in self.CREATIVE_KEYWORDS):
            return "creative"
        if any(kw in prompt_lower for kw in self.REASONING_KEYWORDS):
            return "reasoning"
        if any(kw in prompt_lower for kw in self.FACTUAL_KEYWORDS):
            return "factual"
        return "general"
    
    def _estimate_complexity(self, prompt: str, output: str) -> float:
        """Estimate task complexity based on prompt and output characteristics."""
        complexity = 0.3  # Base complexity
        
        # Longer prompts = more complex
        prompt_words = len(prompt.split())
        if prompt_words > 20:
            complexity += 0.2
        elif prompt_words > 10:
            complexity += 0.1
        
        # Longer outputs = more complex
        output_words = len(output.split())
        if output_words > 100:
            complexity += 0.2
        elif output_words > 50:
            complexity += 0.1
        
        # Questions = more complex
        if "?" in prompt:
            complexity += 0.1
        
        return min(1.0, complexity)
