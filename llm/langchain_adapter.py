"""
LangChain Adapter

Encapsulates all LangChain logic for execution agents.
Exposes simple Python types only - NO LangChain objects leak out.

DESIGN RULES (LOCK THIS IN):
- LangChain stays INSIDE this module
- Only execution agents may use this adapter
- No LangChain imports in: API, Orchestrator, Planner, Analyst, Validator, Evaluator
- Returns (str, dict) tuple only - no LangChain types

BOUNDARY:
    API ❌
    Orchestrator ❌
    Planner ❌
    Analyst ❌
    Validator ❌
    Evaluation ❌
    Execution Agents ✅  ← ONLY HERE
"""

import os
import time
from typing import Dict, Any, Tuple

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_community.callbacks import get_openai_callback

# Load environment variables from .env file
load_dotenv()


def _get_llm() -> AzureChatOpenAI:
    """Get configured AzureChatOpenAI instance."""
    return AzureChatOpenAI(
        azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        openai_api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        temperature=0.7,
    )


def generate(prompt: str, system_prompt: str | None = None) -> Tuple[str, Dict[str, Any]]:
    """
    Generate a response using LangChain AzureChatOpenAI.
    
    Args:
        prompt: The user's prompt
        system_prompt: Optional system prompt for context
        
    Returns:
        Tuple of (output_text, metadata)
        - output_text: The LLM response as a string
        - metadata: dict with model, tokens_used, latency_ms
        
    NO LANGCHAIN TYPES LEAK OUT - only Python primitives.
    """
    llm = _get_llm()
    model = os.environ["AZURE_OPENAI_DEPLOYMENT"]
    
    start_time = time.time()
    
    # Build messages
    messages = []
    if system_prompt:
        from langchain_core.messages import SystemMessage
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))
    
    # Invoke with callback for token tracking
    tokens_used = 0
    try:
        with get_openai_callback() as cb:
            response = llm.invoke(messages)
            tokens_used = cb.total_tokens
    except Exception:
        # Fallback if callback doesn't work
        response = llm.invoke(messages)
    
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Extract content as plain string
    output = response.content if hasattr(response, 'content') else str(response)
    
    metadata = {
        "model": model,
        "tokens_used": tokens_used,
        "latency_ms": latency_ms,
        "provider": "langchain_azure",
    }
    
    return str(output), metadata


def generate_with_tools(
    prompt: str,
    tools: list,
    system_prompt: str | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Generate a response with optional tool calling.
    
    LLM can call tools during generation. Tool results are
    attached to metadata - no LangChain types leak out.
    
    Args:
        prompt: The user's prompt
        tools: List of Tool instances from mcp.tools.base
        system_prompt: Optional system prompt for context
        
    Returns:
        Tuple of (output_text, metadata)
        - output_text: The final LLM response as a string
        - metadata: dict with model, tokens, latency, tool_calls
    """
    from langchain_core.tools import StructuredTool
    from langchain_core.messages import SystemMessage, ToolMessage
    
    llm = _get_llm()
    model = os.environ["AZURE_OPENAI_DEPLOYMENT"]
    
    start_time = time.time()
    tool_calls_log = []
    
    # Convert our tools to LangChain tools
    lc_tools = []
    tool_map = {}
    
    for tool in tools:
        def make_runner(t):
            def runner(**kwargs):
                result = t.run(kwargs)
                return result.model_dump()
            return runner
        
        lc_tool = StructuredTool.from_function(
            func=make_runner(tool),
            name=tool.name,
            description=tool.description,
        )
        lc_tools.append(lc_tool)
        tool_map[tool.name] = tool
    
    # Bind tools to LLM
    llm_with_tools = llm.bind_tools(lc_tools) if lc_tools else llm
    
    # Build messages
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))
    
    # Invoke with callback for token tracking
    tokens_used = 0
    try:
        with get_openai_callback() as cb:
            response = llm_with_tools.invoke(messages)
            tokens_used = cb.total_tokens
    except Exception:
        response = llm_with_tools.invoke(messages)
    
    # Process tool calls if any
    if hasattr(response, 'tool_calls') and response.tool_calls:
        messages.append(response)
        
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            # Execute the tool
            tool = tool_map.get(tool_name)
            if tool:
                tool_result = tool.run(tool_args)
                tool_calls_log.append({
                    "name": tool_name,
                    "input": tool_args,
                    "output": tool_result.output,
                    "success": tool_result.success,
                })
                
                # Add tool result to messages
                messages.append(ToolMessage(
                    content=str(tool_result.output),
                    tool_call_id=tool_call["id"],
                ))
        
        # Get final response after tool execution
        try:
            with get_openai_callback() as cb:
                final_response = llm_with_tools.invoke(messages)
                tokens_used += cb.total_tokens
        except Exception:
            final_response = llm_with_tools.invoke(messages)
        
        output = final_response.content if hasattr(final_response, 'content') else str(final_response)
    else:
        output = response.content if hasattr(response, 'content') else str(response)
    
    latency_ms = int((time.time() - start_time) * 1000)
    
    metadata = {
        "model": model,
        "tokens_used": tokens_used,
        "latency_ms": latency_ms,
        "provider": "langchain_azure",
        "tool_calls": tool_calls_log,
        "tool_count": len(tool_calls_log),
    }
    
    return str(output), metadata


def generate_with_context(
    prompt: str,
    context_documents: list,
    system_prompt: str | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Generate a response grounded in retrieved context.
    
    This is the RAG pattern: context is explicitly passed to the LLM,
    not discovered via tool calling.
    
    Args:
        prompt: The user's prompt
        context_documents: List of retrieved documents, each with 'content' key
        system_prompt: Optional additional system prompt
        
    Returns:
        Tuple of (output_text, metadata)
        - output_text: The LLM response grounded in context
        - metadata: dict with model, tokens, latency, documents_used
    """
    from langchain_core.messages import SystemMessage
    
    llm = _get_llm()
    model = os.environ["AZURE_OPENAI_DEPLOYMENT"]
    
    start_time = time.time()
    
    # Build context string from documents
    context_parts = []
    doc_ids = []
    for i, doc in enumerate(context_documents):
        content = doc.get("content", str(doc))
        doc_id = doc.get("id", f"doc_{i}")
        source = doc.get("source", "unknown")
        doc_ids.append(doc_id)
        context_parts.append(f"[{doc_id}] ({source}): {content}")
    
    context_text = "\n\n".join(context_parts)
    
    # Build system prompt with context
    rag_system_prompt = f"""You are a helpful AI assistant. Answer the user's question based on the following context.

CONTEXT:
{context_text}

INSTRUCTIONS:
- Base your answer on the provided context
- If the context doesn't contain relevant information, say so
- Be accurate and concise"""
    
    if system_prompt:
        rag_system_prompt = f"{system_prompt}\n\n{rag_system_prompt}"
    
    # Build messages
    messages = [
        SystemMessage(content=rag_system_prompt),
        HumanMessage(content=prompt),
    ]
    
    # Invoke with callback for token tracking
    tokens_used = 0
    try:
        with get_openai_callback() as cb:
            response = llm.invoke(messages)
            tokens_used = cb.total_tokens
    except Exception:
        response = llm.invoke(messages)
    
    latency_ms = int((time.time() - start_time) * 1000)
    
    output = response.content if hasattr(response, 'content') else str(response)
    
    metadata = {
        "model": model,
        "tokens_used": tokens_used,
        "latency_ms": latency_ms,
        "provider": "langchain_azure",
        "documents_used": doc_ids,
        "context_length": len(context_text),
    }
    
    return str(output), metadata
