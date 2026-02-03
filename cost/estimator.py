"""
Cost Estimator

Computes per-request cost estimates from execution metadata.

DESIGN RULES:
- Pure function, no side effects
- Never throws (returns 0.0 on error)
- Uses token count from metadata
"""

from typing import Dict, Any, Optional

from cost.model_pricing import get_pricing


def estimate_cost(
    metadata: Dict[str, Any],
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
) -> float:
    """
    Estimate the cost of a request based on metadata.
    
    Args:
        metadata: Execution metadata containing model and tokens_used
        input_tokens: Override input token count (optional)
        output_tokens: Override output token count (optional)
        
    Returns:
        Estimated cost in USD (0.0 on error or missing data)
    """
    try:
        model = metadata.get("model", "unknown")
        pricing = get_pricing(model)
        
        # Get token counts
        # Note: tokens_used in our metadata is total tokens
        # We estimate a 70/30 split if not specified separately
        total_tokens = metadata.get("tokens_used", 0)
        
        if input_tokens is None or output_tokens is None:
            # Estimate split: ~70% input, ~30% output (typical for chat)
            input_tokens = input_tokens or int(total_tokens * 0.7)
            output_tokens = output_tokens or int(total_tokens * 0.3)
        
        # Calculate cost
        input_cost = (input_tokens / 1000) * pricing["input_per_1k"]
        output_cost = (output_tokens / 1000) * pricing["output_per_1k"]
        
        return round(input_cost + output_cost, 8)
        
    except Exception:
        # Never throw - return 0.0 on any error
        return 0.0


def estimate_cost_detailed(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get detailed cost breakdown.
    
    Returns:
        Dict with cost, model, tokens, and breakdown
    """
    try:
        model = metadata.get("model", "unknown")
        pricing = get_pricing(model)
        total_tokens = metadata.get("tokens_used", 0)
        
        input_tokens = int(total_tokens * 0.7)
        output_tokens = int(total_tokens * 0.3)
        
        input_cost = (input_tokens / 1000) * pricing["input_per_1k"]
        output_cost = (output_tokens / 1000) * pricing["output_per_1k"]
        
        return {
            "estimated_cost_usd": round(input_cost + output_cost, 8),
            "model": model,
            "total_tokens": total_tokens,
            "input_tokens_est": input_tokens,
            "output_tokens_est": output_tokens,
            "input_cost_usd": round(input_cost, 8),
            "output_cost_usd": round(output_cost, 8),
            "pricing": pricing,
        }
        
    except Exception as e:
        return {
            "estimated_cost_usd": 0.0,
            "error": str(e),
        }
