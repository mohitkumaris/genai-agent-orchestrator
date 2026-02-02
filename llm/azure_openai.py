"""
Azure OpenAI Client Wrapper

Simple wrapper for Azure OpenAI SDK.
Reads credentials from environment variables (loads from .env file).

DESIGN RULES:
- No retries or error handling frameworks
- No streaming or async logic
- No prompt logging
- No Key Vault integration
"""

import os
import time
from typing import Dict, Any, Tuple

from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables from .env file
load_dotenv()


def generate(prompt: str) -> Tuple[str, Dict[str, Any]]:
    """
    Generate a response from Azure OpenAI.
    
    Args:
        prompt: The user's prompt (passed directly, no system prompt)
        
    Returns:
        Tuple of (response_text, metadata)
        
    Environment Variables Required:
        AZURE_OPENAI_API_KEY: API key for Azure OpenAI
        AZURE_OPENAI_ENDPOINT: Azure OpenAI endpoint URL
        AZURE_OPENAI_DEPLOYMENT: Deployment name (e.g., "gpt-4")
        AZURE_OPENAI_API_VERSION: API version (optional, defaults to 2024-02-15-preview)
    """
    model = os.environ["AZURE_OPENAI_DEPLOYMENT"]
    
    client = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    )
    
    start_time = time.time()
    
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Extract token usage
    tokens_used = 0
    if response.usage:
        tokens_used = response.usage.total_tokens
    
    metadata = {
        "model": model,
        "tokens_used": tokens_used,
        "latency_ms": latency_ms,
    }
    
    output = response.choices[0].message.content or ""
    
    return output, metadata
