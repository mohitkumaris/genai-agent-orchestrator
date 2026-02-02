#!/usr/bin/env python3
"""
Test script for MCP Tools integration.

Demonstrates:
1. Calculator tool usage via GeneralAgent
2. Tool calls tracked in metadata
3. Governance via registry

Run: .venv/bin/python tests/test_tools.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_calculator_tool_direct():
    """Test calculator tool directly."""
    print("=" * 60)
    print("TEST: Calculator tool direct execution")
    print("=" * 60)
    
    from mcp.tools.calculator import CalculatorTool
    
    calc = CalculatorTool()
    
    # Test valid expression
    result = calc.run({"expression": "25 * 4"})
    print(f"  expression: 25 * 4")
    print(f"  result: {result.output}")
    print(f"  success: {result.success}")
    
    assert result.success == True
    assert result.output["result"] == 100
    
    # Test complex expression
    result2 = calc.run({"expression": "(10 + 5) * 2"})
    assert result2.output["result"] == 30
    
    print("  ✅ PASSED\n")


def test_tool_registry():
    """Test tool registry permissions."""
    print("=" * 60)
    print("TEST: Tool registry permissions")
    print("=" * 60)
    
    from mcp.tools.registry import ToolRegistry, bootstrap_tools
    
    # Reset and bootstrap
    ToolRegistry.reset()
    bootstrap_tools()
    
    registry = ToolRegistry.get_instance()
    
    # General agent should have calculator
    general_tools = registry.list_for_agent("general")
    print(f"  Tools for 'general': {[t.name for t in general_tools]}")
    assert len(general_tools) == 1
    assert general_tools[0].name == "calculator"
    
    # Retrieval agent should have retrieval tool
    retrieval_tools = registry.list_for_agent("retrieval")
    print(f"  Tools for 'retrieval': {[t.name for t in retrieval_tools]}")
    assert len(retrieval_tools) == 1
    assert retrieval_tools[0].name == "retrieval"
    
    # Permission checks
    assert registry.is_allowed("calculator", "general") == True
    assert registry.is_allowed("calculator", "retrieval") == False
    assert registry.is_allowed("retrieval", "retrieval") == True
    assert registry.is_allowed("retrieval", "general") == False
    
    print("  ✅ PASSED\n")


def test_general_agent_with_tools():
    """Test GeneralAgent with tools enabled."""
    print("=" * 60)
    print("TEST: GeneralAgent with tools (calculator)")
    print("=" * 60)
    
    from mcp.tools.registry import ToolRegistry, bootstrap_tools
    from agents.general_agent import GeneralAgent
    
    # Reset and bootstrap
    ToolRegistry.reset()
    bootstrap_tools()
    
    # Create tool-enabled agent
    agent = GeneralAgent(enable_tools=True)
    
    print(f"  Tools loaded: {[t.name for t in agent._tools]}")
    assert len(agent._tools) == 1
    
    # Execute with calculation query
    result = agent.run("What is 42 * 17?")
    
    print(f"  output: {result.output[:80]}...")
    print(f"  tool_calls: {result.metadata.get('tool_calls', [])}")
    print(f"  tool_count: {result.metadata.get('tool_count', 0)}")
    
    # Verify tool tracking in metadata
    assert "tool_calls" in result.metadata
    assert "tool_count" in result.metadata
    
    print("  ✅ PASSED\n")


def test_general_agent_without_tools():
    """Test GeneralAgent without tools (existing behavior)."""
    print("=" * 60)
    print("TEST: GeneralAgent without tools (default)")
    print("=" * 60)
    
    from agents.general_agent import GeneralAgent
    
    # Create agent with default (no tools)
    agent = GeneralAgent()  # enable_tools=False by default
    
    print(f"  Tools loaded: {len(agent._tools)}")
    assert len(agent._tools) == 0
    
    # Execute
    result = agent.run("Hello, how are you?")
    
    print(f"  output: {result.output[:80]}...")
    print(f"  provider: {result.metadata.get('provider')}")
    
    # Verify no tool_calls in metadata (regular generate path)
    assert result.metadata.get("tool_calls") is None or result.metadata.get("tool_calls") == []
    
    print("  ✅ PASSED\n")


def test_retrieval_tool_direct():
    """Test retrieval tool directly."""
    print("=" * 60)
    print("TEST: Retrieval tool direct execution")
    print("=" * 60)
    
    from mcp.tools.retrieval import RetrievalTool
    
    tool = RetrievalTool()
    
    # Test retrieval
    result = tool.run({"query": "Python programming", "k": 2})
    
    print(f"  query: Python programming")
    print(f"  success: {result.success}")
    print(f"  documents: {len(result.output.get('documents', []))}")
    
    assert result.success == True
    assert "documents" in result.output
    assert len(result.output["documents"]) == 2
    
    # Verify document structure
    doc = result.output["documents"][0]
    assert "id" in doc
    assert "content" in doc
    assert "score" in doc
    
    print(f"  first doc: {doc['id']} (score: {doc['score']})")
    print("  ✅ PASSED\n")


def test_retrieval_agent_with_tools():
    """Test RetrievalAgent with RAG flow."""
    print("=" * 60)
    print("TEST: RetrievalAgent with tools (RAG flow)")
    print("=" * 60)
    
    from mcp.tools.registry import ToolRegistry, bootstrap_tools
    from agents.retrieval_agent import RetrievalAgent
    
    # Reset and bootstrap
    ToolRegistry.reset()
    bootstrap_tools()
    
    # Create tool-enabled agent
    agent = RetrievalAgent(enable_tools=True)
    
    print(f"  Retrieval tool: {agent._retrieval_tool is not None}")
    assert agent._retrieval_tool is not None
    
    # Execute RAG query
    result = agent.run("What is Python?")
    
    print(f"  output: {result.output[:80]}...")
    print(f"  confidence: {result.confidence}")
    
    # Verify retrieval metadata
    assert "retrieval" in result.metadata
    retrieval_meta = result.metadata["retrieval"]
    print(f"  documents retrieved: {len(retrieval_meta.get('documents', []))}")
    
    assert "documents" in retrieval_meta
    assert len(retrieval_meta["documents"]) > 0
    
    # Verify documents_used tracking
    assert "documents_used" in result.metadata
    
    print("  ✅ PASSED\n")


def run_all_tests():
    """Run all tool tests."""
    print("\n" + "=" * 60)
    print("   MCP TOOLS TEST SUITE")
    print("=" * 60 + "\n")
    
    tests = [
        test_calculator_tool_direct,
        test_tool_registry,
        test_general_agent_without_tools,
        test_general_agent_with_tools,
        test_retrieval_tool_direct,
        test_retrieval_agent_with_tools,
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
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("=" * 60)
    print(f"   RESULTS: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
