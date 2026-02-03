"""
Model Pricing Table

Static pricing configuration for cost estimation.
Prices are in USD per 1K tokens.

DESIGN RULES:
- Configuration only, no logic
- Easy to update when prices change
- Support multiple models
"""

from typing import Dict, Any


# Azure OpenAI / OpenAI pricing (USD per 1K tokens)
# Last updated: 2024-02
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # GPT-4o Mini
    "gpt-4o-mini": {
        "input_per_1k": 0.00015,
        "output_per_1k": 0.0006,
    },
    # GPT-4o
    "gpt-4o": {
        "input_per_1k": 0.0025,
        "output_per_1k": 0.01,
    },
    # GPT-4 Turbo
    "gpt-4-turbo": {
        "input_per_1k": 0.01,
        "output_per_1k": 0.03,
    },
    # GPT-3.5 Turbo
    "gpt-35-turbo": {
        "input_per_1k": 0.0005,
        "output_per_1k": 0.0015,
    },
    "gpt-3.5-turbo": {
        "input_per_1k": 0.0005,
        "output_per_1k": 0.0015,
    },
}

# Default pricing for unknown models (conservative estimate)
DEFAULT_PRICING = {
    "input_per_1k": 0.001,
    "output_per_1k": 0.002,
}


def get_pricing(model: str) -> Dict[str, float]:
    """
    Get pricing for a model.
    
    Args:
        model: Model name (e.g., 'gpt-4o-mini')
        
    Returns:
        Dict with input_per_1k and output_per_1k prices
    """
    # Direct match
    if model in MODEL_PRICING:
        return MODEL_PRICING[model]
    
    # Fuzzy match (handle deployment name variations)
    model_lower = model.lower()
    for known_model, pricing in MODEL_PRICING.items():
        if known_model in model_lower or model_lower in known_model:
            return pricing
    
    # Default fallback
    return DEFAULT_PRICING
