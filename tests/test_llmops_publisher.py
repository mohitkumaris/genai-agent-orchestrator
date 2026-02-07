#!/usr/bin/env python3
"""
LLMOps Publisher Tests

Verifies fire-and-forget semantics:
- Publisher never raises exceptions
- Correct payload construction (facts only)
- Timeout enforcement
- Graceful degradation when LLMOps is down
- Disabled mode produces no HTTP calls

Run: python3 tests/test_llmops_publisher.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import urllib.error

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from observability.trace import ExecutionTrace
from observability.llmops_publisher import (
    _build_trace_payload,
    _build_cost_payload,
    _build_evaluation_payload,
    _build_policy_payload,
    _build_sla_payload,
    publish_all,
    publish_trace,
    is_enabled,
    _post,
)


def create_test_trace() -> ExecutionTrace:
    """Create a sample ExecutionTrace for testing."""
    started_at = datetime.now() - timedelta(milliseconds=150)
    finished_at = datetime.now()
    
    return ExecutionTrace(
        request_id="test-req-001",
        agent_name="general",
        success=True,
        started_at=started_at,
        finished_at=finished_at,
        metadata={
            "session_id": "session-123",
            "model": "gpt-4o",
            "estimated_cost_usd": 0.0025,
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "routing": {
                "analysis": {
                    "grounding_score": 0.85,
                },
            },
            "validation": {
                "is_safe": True,
                "grounding_score": 0.9,
            },
            "policy": {
                "status": "pass",
                "violations": [],
                "warnings": ["high_cost"],
                "checked_rules": 5,
            },
            "sla": {
                "tier": "free",
                "limits": {"max_tokens": 1000},
            },
        },
        error=None,
    )


def test_trace_payload_construction():
    """Test: Trace payload contains expected fields."""
    print("=" * 60)
    print("TEST: Trace payload construction")
    print("=" * 60)
    
    trace = create_test_trace()
    payload = _build_trace_payload(trace)
    
    assert payload["request_id"] == "test-req-001"
    assert payload["agent_name"] == "general"
    assert payload["success"] == True
    assert "started_at" in payload
    assert "finished_at" in payload
    assert payload["latency_ms"] >= 0
    assert payload["session_id"] == "session-123"
    
    print("  ✅ PASSED\n")


def test_cost_payload_construction():
    """Test: Cost payload extracts token and cost data."""
    print("=" * 60)
    print("TEST: Cost payload construction")
    print("=" * 60)
    
    trace = create_test_trace()
    payload = _build_cost_payload(trace)
    
    assert payload["request_id"] == "test-req-001"
    assert payload["model"] == "gpt-4o"
    assert payload["input_tokens"] == 100
    assert payload["output_tokens"] == 50
    assert payload["total_tokens"] == 150
    assert payload["estimated_cost_usd"] == 0.0025
    assert payload["agent_name"] == "general"
    
    print("  ✅ PASSED\n")


def test_evaluation_payload_construction():
    """Test: Evaluation payload extracts grounding score."""
    print("=" * 60)
    print("TEST: Evaluation payload construction")
    print("=" * 60)
    
    trace = create_test_trace()
    payload = _build_evaluation_payload(trace)
    
    assert payload["request_id"] == "test-req-001"
    assert payload["score"] == 0.9  # From validation.grounding_score
    assert payload["passed"] == True
    assert payload["evaluator"] == "critic"
    
    print("  ✅ PASSED\n")


def test_policy_payload_construction():
    """Test: Policy payload extracts violations and warnings."""
    print("=" * 60)
    print("TEST: Policy payload construction")
    print("=" * 60)
    
    trace = create_test_trace()
    payload = _build_policy_payload(trace)
    
    assert payload["request_id"] == "test-req-001"
    assert payload["status"] == "pass"
    assert payload["violations"] == []
    assert payload["warnings"] == ["high_cost"]
    assert payload["checked_rules"] == 5
    
    print("  ✅ PASSED\n")


def test_sla_payload_construction():
    """Test: SLA payload extracts tier and limits."""
    print("=" * 60)
    print("TEST: SLA payload construction")
    print("=" * 60)
    
    trace = create_test_trace()
    payload = _build_sla_payload(trace)
    
    assert payload["request_id"] == "test-req-001"
    assert payload["tier"] == "free"
    assert payload["limits"]["max_tokens"] == 1000
    
    print("  ✅ PASSED\n")


def test_publisher_never_raises_on_connection_error():
    """Test: Publisher never raises even with connection errors."""
    print("=" * 60)
    print("TEST: Publisher never raises on connection error")
    print("=" * 60)
    
    trace = create_test_trace()
    
    # Mock urlopen to raise connection error
    with patch.dict(os.environ, {"LLMOPS_ENABLED": "true", "LLMOPS_BASE_URL": "http://localhost:9999"}):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
            
            # This should NOT raise
            try:
                publish_trace(trace)
                print("  ✓ No exception raised on URLError")
            except Exception as e:
                print(f"  ❌ FAILED: Raised {type(e).__name__}: {e}")
                raise AssertionError("Publisher should never raise")
    
    print("  ✅ PASSED\n")


def test_publisher_never_raises_on_timeout():
    """Test: Publisher never raises on timeout."""
    print("=" * 60)
    print("TEST: Publisher never raises on timeout")
    print("=" * 60)
    
    trace = create_test_trace()
    
    import socket
    
    with patch.dict(os.environ, {"LLMOPS_ENABLED": "true"}):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = socket.timeout("timed out")
            
            # This should NOT raise
            try:
                publish_all(trace)
                print("  ✓ No exception raised on timeout")
            except Exception as e:
                print(f"  ❌ FAILED: Raised {type(e).__name__}: {e}")
                raise AssertionError("Publisher should never raise")
    
    print("  ✅ PASSED\n")


def test_disabled_mode_no_http_calls():
    """Test: When disabled, no HTTP calls are made."""
    print("=" * 60)
    print("TEST: Disabled mode produces no HTTP calls")
    print("=" * 60)
    
    trace = create_test_trace()
    
    with patch.dict(os.environ, {"LLMOPS_ENABLED": "false"}):
        with patch("urllib.request.urlopen") as mock_urlopen:
            publish_all(trace)
            
            mock_urlopen.assert_not_called()
            print("  ✓ No HTTP calls when disabled")
    
    print("  ✅ PASSED\n")


def test_enabled_mode_makes_http_calls():
    """Test: When enabled, HTTP calls are made."""
    print("=" * 60)
    print("TEST: Enabled mode makes HTTP calls")
    print("=" * 60)
    
    trace = create_test_trace()
    
    # Create mock response
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"id":"test","ingested_at":"2026-01-01T00:00:00"}'
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    
    with patch.dict(os.environ, {"LLMOPS_ENABLED": "true", "LLMOPS_BASE_URL": "http://localhost:8001"}):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = mock_response
            
            publish_all(trace)
            
            # Should have made 5 calls: trace, cost, evaluation, policy, sla
            assert mock_urlopen.call_count == 5, f"Expected 5 calls, got {mock_urlopen.call_count}"
            print(f"  ✓ Made {mock_urlopen.call_count} HTTP calls")
    
    print("  ✅ PASSED\n")


def test_is_enabled_respects_environment():
    """Test: is_enabled() respects LLMOPS_ENABLED env var."""
    print("=" * 60)
    print("TEST: is_enabled() respects environment")
    print("=" * 60)
    
    with patch.dict(os.environ, {"LLMOPS_ENABLED": "true"}):
        assert is_enabled() == True, "Should be enabled when LLMOPS_ENABLED=true"
        print("  ✓ Enabled when LLMOPS_ENABLED=true")
    
    with patch.dict(os.environ, {"LLMOPS_ENABLED": "false"}):
        assert is_enabled() == False, "Should be disabled when LLMOPS_ENABLED=false"
        print("  ✓ Disabled when LLMOPS_ENABLED=false")
    
    with patch.dict(os.environ, {}, clear=True):
        # Remove LLMOPS_ENABLED to test default
        os.environ.pop("LLMOPS_ENABLED", None)
        assert is_enabled() == False, "Should be disabled by default"
        print("  ✓ Disabled by default")
    
    print("  ✅ PASSED\n")


def test_payload_with_missing_metadata():
    """Test: Payloads handle missing metadata gracefully."""
    print("=" * 60)
    print("TEST: Payloads handle missing metadata")
    print("=" * 60)
    
    # Create minimal trace with empty metadata
    trace = ExecutionTrace(
        request_id="test-minimal",
        agent_name="general",
        success=True,
        started_at=datetime.now() - timedelta(milliseconds=50),
        finished_at=datetime.now(),
        metadata={},
        error=None,
    )
    
    # All payload builders should handle missing data gracefully
    trace_payload = _build_trace_payload(trace)
    assert trace_payload["request_id"] == "test-minimal"
    print("  ✓ Trace payload OK with empty metadata")
    
    cost_payload = _build_cost_payload(trace)
    assert cost_payload["estimated_cost_usd"] == 0.0
    assert cost_payload["total_tokens"] == 0
    print("  ✓ Cost payload OK with empty metadata")
    
    eval_payload = _build_evaluation_payload(trace)
    assert eval_payload["score"] == 0.0
    print("  ✓ Evaluation payload OK with empty metadata")
    
    policy_payload = _build_policy_payload(trace)
    assert policy_payload is None  # No policy metadata means no payload
    print("  ✓ Policy payload returns None with empty metadata")
    
    sla_payload = _build_sla_payload(trace)
    assert sla_payload is None  # No SLA metadata means no payload
    print("  ✓ SLA payload returns None with empty metadata")
    
    print("  ✅ PASSED\n")


def run_all_tests():
    """Run all LLMOps publisher tests."""
    print("\n" + "=" * 60)
    print("   LLMOPS PUBLISHER TEST SUITE")
    print("=" * 60 + "\n")
    
    tests = [
        test_trace_payload_construction,
        test_cost_payload_construction,
        test_evaluation_payload_construction,
        test_policy_payload_construction,
        test_sla_payload_construction,
        test_publisher_never_raises_on_connection_error,
        test_publisher_never_raises_on_timeout,
        test_disabled_mode_no_http_calls,
        test_enabled_mode_makes_http_calls,
        test_is_enabled_respects_environment,
        test_payload_with_missing_metadata,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ FAILED: {e}\n")
            failed += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}\n")
            failed += 1
    
    print("=" * 60)
    print(f"   RESULTS: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
