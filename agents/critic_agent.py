"""
Critic (Validator) Agent

The last line of defense before user exposure.

DESIGN RULES (NON-NEGOTIABLE):
- Does NOT generate user-facing answers
- Does NOT rewrite content  
- Does NOT call MCP tools
- Does NOT access databases
- Does NOT invoke RAG
- Does NOT re-plan execution

It ONLY evaluates and produces structured CriticResult objects.

DESIGN PHILOSOPHY:
- Trust is more important than fluency
- A blocked answer is better than a hallucinated one
- Fail safe, not smart
- If uncertain, escalate risk
"""

from typing import Any, Dict, List, Optional

from agents.base import BaseAgent
from schemas.plan import PlanStep
from schemas.result import (
    AgentResult,
    CriticResult,
    Recommendation,
    RiskLevel,
    ValidatedClaim,
)
from schemas.request import ServiceRequest
from schemas.response import ServiceResponse
from genai_mcp_core.context import MCPContext
from orchestration.state import StepResult


class CriticAgent(BaseAgent):
    """
    Evaluates intermediate or final outputs for safety, grounding, and risk.
    
    This agent is stateless, deterministic where possible, and conservative
    (prefers false negatives — blocking safe content over passing unsafe content).
    """

    def __init__(self):
        super().__init__("critic_agent")

    def run_step(
        self,
        *,
        step: PlanStep,
        context: MCPContext,
        previous_results: Optional[List[StepResult]] = None,
    ) -> AgentResult:
        """
        Evaluate the proposed output against retrieved context.
        
        This is the structured interface for plan-based validation.
        
        Args:
            step: The current plan step being executed.
            context: MCP context (immutable request envelope).
            previous_results: Results from prior steps (contains retrieved chunks, proposed output).
            
        Returns:
            AgentResult containing a CriticResult object.
        """
        issues: List[str] = []
        validated_claims: List[ValidatedClaim] = []
        
        # Extract input data from previous step results
        input_data = self._extract_input_data(step, previous_results or [])
        
        retrieved_chunks = input_data.get("retrieved_chunks", [])
        proposed_output = input_data.get("proposed_output")
        metadata = input_data.get("metadata", {})

        # --- Validation Checks ---
        
        # 1. Presence Check: Grounding context
        if not retrieved_chunks:
            issues.append("No grounding context available")
        
        # 2. Presence Check: Output to evaluate
        if proposed_output is None:
            issues.append("No output to evaluate")
        
        # 3. Grounding Check
        grounding_score = 0.0
        if retrieved_chunks and proposed_output:
            grounding_score, grounding_issues, validated_claims = self._check_grounding(
                proposed_output=proposed_output,
                retrieved_chunks=retrieved_chunks,
            )
            issues.extend(grounding_issues)
        
        # 4. Metadata Completeness Check
        metadata_issues = self._check_metadata_completeness(metadata)
        issues.extend(metadata_issues)
        
        # 5. Confidence Check
        confidence_score = self._compute_confidence(
            grounding_score=grounding_score,
            num_chunks=len(retrieved_chunks),
            num_issues=len(issues),
        )

        # --- Risk Assessment ---
        risk_level = self._assess_risk(
            issues=issues,
            grounding_score=grounding_score,
            confidence_score=confidence_score,
        )

        # --- Recommendation ---
        recommendation = self._compute_recommendation(
            risk_level=risk_level,
            issues=issues,
        )

        # --- Final Verdict ---
        is_safe = recommendation == Recommendation.PROCEED

        result = CriticResult(
            is_safe=is_safe,
            risk_level=risk_level,
            issues=issues,
            recommendation=recommendation,
            validated_claims=validated_claims,
            grounding_score=grounding_score,
            confidence_score=confidence_score,
        )

        return AgentResult.success(
            agent="critic",
            output=result,
            metadata={
                "step_id": step.step_id,
                "num_chunks_evaluated": len(retrieved_chunks),
                "num_issues_found": len(issues),
            },
        )

    def _extract_input_data(
        self,
        step: PlanStep,
        previous_results: List[StepResult],
    ) -> Dict[str, Any]:
        """
        Extract retrieved_chunks and proposed_output from previous step results.
        
        Convention:
        - Retrieval step output contains chunks
        - Generation step output contains proposed_output
        """
        input_data: Dict[str, Any] = {}
        
        # Check if step.input has explicit data
        if step.input:
            if isinstance(step.input, dict):
                input_data.update(step.input)
        
        # Extract from previous step results
        for prev_result in previous_results:
            if prev_result.agent_role in ("retrieval", "retrieval_agent"):
                # Retrieval agent output is the chunks
                output = prev_result.output
                if isinstance(output, dict) and "chunks" in output:
                    input_data["retrieved_chunks"] = output["chunks"]
                elif isinstance(output, list):
                    input_data["retrieved_chunks"] = output
                else:
                    # Treat raw output as a single chunk
                    input_data["retrieved_chunks"] = [output] if output else []
                    
            elif prev_result.agent_role in ("general", "general_agent", "generator"):
                # Generator output is the proposed answer
                input_data["proposed_output"] = prev_result.output
                
            # Collect metadata from all steps
            if prev_result.metadata:
                input_data.setdefault("metadata", {}).update(prev_result.metadata)
        
        return input_data

    def _check_grounding(
        self,
        proposed_output: Any,
        retrieved_chunks: List[Any],
    ) -> tuple[float, List[str], List[ValidatedClaim]]:
        """
        Verify that the proposed output is grounded in the retrieved context.
        
        Returns:
            Tuple of (grounding_score, issues, validated_claims)
        """
        issues: List[str] = []
        validated_claims: List[ValidatedClaim] = []
        
        # Convert output to string for analysis
        output_text = str(proposed_output).lower()
        
        # Build context corpus from chunks
        context_corpus = self._build_context_corpus(retrieved_chunks)
        
        if not context_corpus:
            issues.append("Retrieved chunks contain no extractable text")
            return 0.0, issues, validated_claims
        
        # Simple keyword-based grounding check
        # In production, this would use semantic similarity
        output_words = set(output_text.split())
        context_words = set(context_corpus.lower().split())
        
        # Remove common stop words for more meaningful comparison
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", 
                      "being", "have", "has", "had", "do", "does", "did", "will",
                      "would", "could", "should", "may", "might", "must", "shall",
                      "can", "need", "dare", "ought", "used", "to", "of", "in",
                      "for", "on", "with", "at", "by", "from", "as", "into", "through",
                      "during", "before", "after", "above", "below", "between",
                      "under", "again", "further", "then", "once", "and", "but",
                      "or", "nor", "so", "yet", "both", "either", "neither", "not",
                      "only", "own", "same", "than", "too", "very", "just", "also"}
        
        output_keywords = output_words - stop_words
        context_keywords = context_words - stop_words
        
        if not output_keywords:
            # Output is too generic to evaluate
            issues.append("Output contains no substantive content to evaluate")
            return 0.5, issues, validated_claims
        
        # Calculate overlap
        overlap = output_keywords & context_keywords
        grounding_score = len(overlap) / len(output_keywords) if output_keywords else 0.0
        
        # Create a validated claim for the overall output
        validated_claims.append(
            ValidatedClaim(
                claim_text=output_text[:200] + "..." if len(output_text) > 200 else output_text,
                is_grounded=grounding_score >= 0.3,
                confidence=grounding_score,
                supporting_chunk_ids=[str(i) for i in range(len(retrieved_chunks))],
            )
        )
        
        # Flag low grounding
        if grounding_score < 0.3:
            issues.append(f"Low grounding score ({grounding_score:.2f}): output may not be supported by context")
        elif grounding_score < 0.5:
            issues.append(f"Moderate grounding score ({grounding_score:.2f}): some claims may be unsupported")
        
        return grounding_score, issues, validated_claims

    def _build_context_corpus(self, retrieved_chunks: List[Any]) -> str:
        """Build a text corpus from retrieved chunks."""
        texts = []
        for chunk in retrieved_chunks:
            if isinstance(chunk, dict):
                # Try common keys for chunk text
                text = chunk.get("text") or chunk.get("content") or chunk.get("page_content") or ""
                texts.append(str(text))
            elif isinstance(chunk, str):
                texts.append(chunk)
            else:
                texts.append(str(chunk))
        return " ".join(texts)

    def _check_metadata_completeness(self, metadata: Dict[str, Any]) -> List[str]:
        """Check for missing or incomplete metadata."""
        issues: List[str] = []
        
        # Define expected metadata fields
        expected_fields = ["source", "timestamp"]
        
        for field in expected_fields:
            if field not in metadata:
                issues.append(f"Missing metadata: {field}")
        
        return issues

    def _compute_confidence(
        self,
        grounding_score: float,
        num_chunks: int,
        num_issues: int,
    ) -> float:
        """
        Compute overall confidence in the validation.
        
        Higher grounding + more chunks + fewer issues = higher confidence.
        """
        # Base confidence from grounding
        confidence = grounding_score * 0.6
        
        # Boost for having multiple chunks
        if num_chunks >= 3:
            confidence += 0.2
        elif num_chunks >= 1:
            confidence += 0.1
        
        # Penalty for issues
        issue_penalty = min(num_issues * 0.1, 0.3)
        confidence -= issue_penalty
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, confidence))

    def _assess_risk(
        self,
        issues: List[str],
        grounding_score: float,
        confidence_score: float,
    ) -> RiskLevel:
        """
        Determine risk level based on validation results.
        
        Conservative approach: when in doubt, escalate risk.
        """
        # Critical issues = HIGH risk
        critical_keywords = ["no grounding", "no output", "no extractable"]
        for issue in issues:
            if any(kw in issue.lower() for kw in critical_keywords):
                return RiskLevel.HIGH
        
        # Low grounding = HIGH risk
        if grounding_score < 0.2:
            return RiskLevel.HIGH
        
        # Moderate issues or grounding = MEDIUM risk
        if len(issues) > 2 or grounding_score < 0.5:
            return RiskLevel.MEDIUM
        
        # High confidence and few issues = LOW risk
        if confidence_score >= 0.6 and len(issues) <= 1:
            return RiskLevel.LOW
        
        # Default to MEDIUM (conservative)
        return RiskLevel.MEDIUM

    def _compute_recommendation(
        self,
        risk_level: RiskLevel,
        issues: List[str],
    ) -> Recommendation:
        """
        Derive action recommendation from risk level and issues.
        
        Philosophy: Block > Warn > Proceed
        """
        if risk_level == RiskLevel.HIGH:
            return Recommendation.BLOCK
        
        if risk_level == RiskLevel.MEDIUM:
            # Check if issues are severe enough to block
            severe_keywords = ["no grounding", "no output", "unsupported"]
            for issue in issues:
                if any(kw in issue.lower() for kw in severe_keywords):
                    return Recommendation.BLOCK
            return Recommendation.WARN
        
        # LOW risk
        return Recommendation.PROCEED

    # --- Post-Execution Validation API ---
    
    def validate_from_execution(
        self,
        execution_result: "ExecutionResult",
    ) -> CriticResult:
        """
        Validate aggregated execution result.
        
        Called by OrchestrationRouter AFTER execution completes.
        This is the primary validation API for the end-to-end flow.
        
        Args:
            execution_result: Result from OrchestrationExecutor
            
        Returns:
            CriticResult: Structured validation output
        """
        from orchestration.state import ExecutionResult as ER, StepResult, StepStatus
        
        issues: List[str] = []
        validated_claims: List[ValidatedClaim] = []
        
        # Check execution status
        if execution_result.status == StepStatus.FAILED:
            issues.append("Execution failed")
        
        # Extract data from step results
        retrieved_chunks: List[Any] = []
        proposed_output: Optional[str] = None
        metadata: Dict[str, Any] = {}
        
        for step_result in execution_result.step_results:
            if step_result.agent_role in ("retrieval", "retrieval_agent"):
                output = step_result.output
                if isinstance(output, dict) and "chunks" in output:
                    retrieved_chunks.extend(output["chunks"])
                elif isinstance(output, list):
                    retrieved_chunks.extend(output)
                elif output:
                    retrieved_chunks.append(output)
                    
            elif step_result.agent_role in ("general", "general_agent", "generator"):
                proposed_output = step_result.output
                
            if step_result.metadata:
                metadata.update(step_result.metadata)
        
        # Use final_output if no generation step
        if proposed_output is None:
            proposed_output = execution_result.final_output
        
        # --- Validation Checks ---
        
        if not retrieved_chunks:
            issues.append("No grounding context available")
        
        if proposed_output is None:
            issues.append("No output to evaluate")
        
        # Grounding check
        grounding_score = 0.0
        if retrieved_chunks and proposed_output:
            grounding_score, grounding_issues, validated_claims = self._check_grounding(
                proposed_output=proposed_output,
                retrieved_chunks=retrieved_chunks,
            )
            issues.extend(grounding_issues)
        
        # Metadata check
        metadata_issues = self._check_metadata_completeness(metadata)
        issues.extend(metadata_issues)
        
        # Confidence
        confidence_score = self._compute_confidence(
            grounding_score=grounding_score,
            num_chunks=len(retrieved_chunks),
            num_issues=len(issues),
        )
        
        # Risk assessment
        risk_level = self._assess_risk(
            issues=issues,
            grounding_score=grounding_score,
            confidence_score=confidence_score,
        )
        
        # Recommendation
        recommendation = self._compute_recommendation(
            risk_level=risk_level,
            issues=issues,
        )
        
        is_safe = recommendation == Recommendation.PROCEED
        
        return CriticResult(
            is_safe=is_safe,
            risk_level=risk_level,
            issues=issues,
            recommendation=recommendation,
            validated_claims=validated_claims,
            grounding_score=grounding_score,
            confidence_score=confidence_score,
        )

    # --- Bridge for Executor Compatibility ---
    
    async def execute(self, request: ServiceRequest) -> ServiceResponse:
        """
        Bridge method for compatibility with OrchestrationExecutor.
        
        The executor passes ServiceRequest but the Critic requires structured
        input from previous steps. This bridge creates a minimal valid context.
        """
        # Create minimal context and step
        ctx = MCPContext.create()
        step = PlanStep(
            step_id=0,
            agent_role="critic",
            intent="validate_output",
            description="Bridge execution from legacy interface",
            input={
                "proposed_output": request.query,
                "retrieved_chunks": request.context.get("retrieved_chunks", []),
                "metadata": request.context,
            },
        )
        
        result = self.run_step(step=step, context=ctx, previous_results=[])
        
        # Extract CriticResult for response
        critic_result: CriticResult = result.output
        
        return ServiceResponse(
            answer=f"Validation: {critic_result.recommendation.value}",
            metadata={
                "is_safe": critic_result.is_safe,
                "risk_level": critic_result.risk_level.value,
                "issues": critic_result.issues,
                "grounding_score": critic_result.grounding_score,
            },
        )

    def run(self, prompt: str) -> str:
        """
        Simple synchronous interface for agent execution.
        
        Provides minimal typed contract compliance with BaseAgent.
        For CriticAgent, this creates a minimal validation context.
        """
        ctx = MCPContext.create()
        step = PlanStep(
            step_id=0,
            agent_role="critic",
            intent="simple_validation",
            description="Simple validation from prompt",
            input={
                "proposed_output": prompt,
                "retrieved_chunks": [],
                "metadata": {},
            },
        )
        result = self.run_step(step=step, context=ctx, previous_results=[])
        critic_result: CriticResult = result.output
        return f"Validation: {critic_result.recommendation.value}, Safe: {critic_result.is_safe}"


# Type hint for forward reference
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from orchestration.state import ExecutionResult
