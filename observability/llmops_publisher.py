"""
LLMOps Publisher

Fire-and-forget publisher for sending observability data to LLMOps platform.

DESIGN RULES (NON-NEGOTIABLE):
- HTTP POST only (no reads)
- Fire-and-forget (non-blocking)
- Short timeout (≤ 500ms)
- Never raise exceptions
- Log failures as warnings only
- No imports from agents, planner, policy, memory, ml, anomaly

This module exists solely to forward facts about execution.
It must NEVER influence execution or delay responses.
"""

import os
import logging
from typing import Any, Dict, Optional

# Use urllib to avoid external dependencies
import urllib.request
import urllib.error
import json
import socket

from observability.trace import ExecutionTrace


logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

def _get_config() -> Dict[str, Any]:
    """Get LLMOps configuration from environment."""
    return {
        "enabled": os.getenv("LLMOPS_ENABLED", "false").lower() == "true",
        "base_url": os.getenv("LLMOPS_BASE_URL", "http://localhost:8001"),
        "timeout_ms": int(os.getenv("LLMOPS_TIMEOUT_MS", "500")),
    }


def is_enabled() -> bool:
    """Check if LLMOps publishing is enabled."""
    return _get_config()["enabled"]


# ============================================================
# LOW-LEVEL HTTP (Fire and Forget)
# ============================================================

def _post(endpoint: str, payload: Dict[str, Any]) -> None:
    """
    POST payload to LLMOps endpoint.
    
    GUARANTEES:
    - Never raises exceptions
    - Returns within timeout
    - Logs failures as warnings
    """
    config = _get_config()
    
    if not config["enabled"]:
        return
    
    url = f"{config['base_url']}{endpoint}"
    timeout_seconds = config["timeout_ms"] / 1000.0
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        
        # Set socket timeout for non-blocking behavior
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            # We don't care about the response, just that it succeeded
            _ = response.read()
            
    except urllib.error.URLError as e:
        logger.warning(f"[LLMOPS] Failed to POST to {endpoint}: {e}")
    except socket.timeout:
        logger.warning(f"[LLMOPS] Timeout posting to {endpoint}")
    except Exception as e:
        logger.warning(f"[LLMOPS] Unexpected error posting to {endpoint}: {e}")


# ============================================================
# PAYLOAD BUILDERS (Facts Only)
# ============================================================

def _build_trace_payload(trace: ExecutionTrace) -> Dict[str, Any]:
    """Build trace ingestion payload from ExecutionTrace."""
    return {
        "request_id": trace.request_id,
        "agent_name": trace.agent_name,
        "success": trace.success,
        "started_at": trace.started_at.isoformat(),
        "finished_at": trace.finished_at.isoformat(),
        "latency_ms": trace.latency_ms,
        "metadata": trace.metadata,
        "session_id": trace.metadata.get("session_id"),
        "error": trace.error,
    }


def _build_cost_payload(trace: ExecutionTrace) -> Optional[Dict[str, Any]]:
    """Build cost ingestion payload from ExecutionTrace metadata."""
    cost_usd = trace.metadata.get("estimated_cost_usd", 0.0)
    
    # Extract token counts from routing metadata if available
    routing = trace.metadata.get("routing", {})
    analysis = routing.get("analysis", {})
    
    # Get model from metadata
    model = trace.metadata.get("model", "unknown")
    if model == "unknown":
        model = routing.get("model", "unknown")
    
    # Token counts - look in multiple places
    input_tokens = trace.metadata.get("input_tokens", 0)
    output_tokens = trace.metadata.get("output_tokens", 0)
    total_tokens = trace.metadata.get("total_tokens", input_tokens + output_tokens)
    
    return {
        "request_id": trace.request_id,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": cost_usd,
        "session_id": trace.metadata.get("session_id"),
        "agent_name": trace.agent_name,
    }


def _build_evaluation_payload(trace: ExecutionTrace) -> Optional[Dict[str, Any]]:
    """Build evaluation ingestion payload from ExecutionTrace metadata."""
    routing = trace.metadata.get("routing", {})
    analysis = routing.get("analysis", {})
    validation = trace.metadata.get("validation", {})
    
    # Get grounding score from validation or analysis
    grounding_score = validation.get("grounding_score", 0.0)
    if grounding_score == 0.0:
        grounding_score = analysis.get("grounding_score", 0.0)
    
    # Determine if passed based on success and safety
    is_safe = validation.get("is_safe", True)
    passed = trace.success and is_safe
    
    return {
        "request_id": trace.request_id,
        "score": grounding_score,
        "passed": passed,
        "evaluator": "critic",
        "details": {
            "validation": validation,
            "analysis": analysis,
        },
        "session_id": trace.metadata.get("session_id"),
    }


def _build_policy_payload(trace: ExecutionTrace) -> Optional[Dict[str, Any]]:
    """Build policy outcome ingestion payload from ExecutionTrace metadata."""
    policy = trace.metadata.get("policy", {})
    
    if not policy:
        return None
    
    status = policy.get("status", "pass")
    violations = policy.get("violations", [])
    warnings = policy.get("warnings", [])
    checked_rules = policy.get("checked_rules", 0)
    
    return {
        "request_id": trace.request_id,
        "status": status,
        "violations": violations,
        "warnings": warnings,
        "checked_rules": checked_rules,
        "session_id": trace.metadata.get("session_id"),
    }


def _build_sla_payload(trace: ExecutionTrace) -> Optional[Dict[str, Any]]:
    """Build SLA ingestion payload from ExecutionTrace metadata."""
    sla = trace.metadata.get("sla", {})
    
    if not sla:
        return None
    
    tier = sla.get("tier", "unknown")
    limits = sla.get("limits", {})
    
    return {
        "request_id": trace.request_id,
        "tier": tier,
        "limits": limits,
        "session_id": trace.metadata.get("session_id"),
    }


# ============================================================
# PUBLIC API
# ============================================================

def publish_trace(trace: ExecutionTrace) -> None:
    """
    Publish trace record to LLMOps.
    
    Fire-and-forget. Never raises. Never blocks.
    """
    payload = _build_trace_payload(trace)
    _post("/ingest/trace", payload)


def publish_cost(trace: ExecutionTrace) -> None:
    """
    Publish cost record to LLMOps.
    
    Fire-and-forget. Never raises. Never blocks.
    """
    payload = _build_cost_payload(trace)
    if payload:
        _post("/ingest/cost", payload)


def publish_evaluation(trace: ExecutionTrace) -> None:
    """
    Publish evaluation record to LLMOps.
    
    Fire-and-forget. Never raises. Never blocks.
    """
    payload = _build_evaluation_payload(trace)
    if payload:
        _post("/ingest/evaluation", payload)


def publish_policy(trace: ExecutionTrace) -> None:
    """
    Publish policy outcome to LLMOps.
    
    Fire-and-forget. Never raises. Never blocks.
    """
    payload = _build_policy_payload(trace)
    if payload:
        _post("/ingest/policy", payload)


def publish_sla(trace: ExecutionTrace) -> None:
    """
    Publish SLA record to LLMOps.
    
    Fire-and-forget. Never raises. Never blocks.
    """
    payload = _build_sla_payload(trace)
    if payload:
        _post("/ingest/sla", payload)


def publish_all(trace: ExecutionTrace) -> None:
    """
    Publish all records to LLMOps.
    
    Convenience function that calls all individual publishers.
    Fire-and-forget. Never raises. Never blocks.
    
    Order: trace → cost → evaluation → policy → sla
    """
    if not is_enabled():
        return
    
    publish_trace(trace)
    publish_cost(trace)
    publish_evaluation(trace)
    publish_policy(trace)
    publish_sla(trace)
