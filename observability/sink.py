"""
Trace Sink Interface

Abstract sink for trace output.
Storage-agnostic - implementations can write to console, file, cloud, etc.

DESIGN RULES:
- Side-effect only
- Never throw exceptions
- Storage-agnostic interface
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from observability.trace import ExecutionTrace


class TraceSink(ABC):
    """
    Abstract base for trace output destinations.
    
    Implementations:
    - ConsoleTraceSink (default)
    - FileTraceSink (future)
    - CloudTraceSink (future - App Insights, etc.)
    """
    
    @abstractmethod
    def emit(self, trace: ExecutionTrace) -> None:
        """
        Emit a trace to the sink.
        
        Must not throw - failures should be logged and ignored.
        """
        pass


class ConsoleTraceSink(TraceSink):
    """
    Default sink that prints traces to console.
    
    Format: structured but human-readable.
    """
    
    def __init__(self, verbose: bool = True):
        """
        Initialize console sink.
        
        Args:
            verbose: If True, print full metadata. If False, summary only.
        """
        self._verbose = verbose
    
    def emit(self, trace: ExecutionTrace) -> None:
        """Print trace to console."""
        try:
            status = "✓" if trace.success else "✗"
            
            print(f"\n{'='*60}")
            print(f"[TRACE] {status} {trace.request_id[:8]}...")
            print(f"{'='*60}")
            print(f"  Agent:    {trace.agent_name}")
            print(f"  Success:  {trace.success}")
            print(f"  Latency:  {trace.latency_ms}ms")
            print(f"  Started:  {trace.started_at.strftime('%H:%M:%S.%f')[:-3]}")
            print(f"  Finished: {trace.finished_at.strftime('%H:%M:%S.%f')[:-3]}")
            
            if trace.error:
                print(f"  Error:    {trace.error}")
            
            if self._verbose and trace.metadata:
                print(f"\n  Metadata:")
                self._print_metadata(trace.metadata, indent=4)
            
            print(f"{'='*60}\n")
            
        except Exception as e:
            # Never throw - just log failure
            print(f"[TRACE ERROR] Failed to emit trace: {e}")
    
    def _print_metadata(self, data: dict, indent: int = 0) -> None:
        """Recursively print metadata with indentation."""
        prefix = " " * indent
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"{prefix}{key}:")
                self._print_metadata(value, indent + 2)
            elif isinstance(value, list):
                print(f"{prefix}{key}: [{len(value)} items]")
            else:
                # Truncate long values
                str_val = str(value)
                if len(str_val) > 60:
                    str_val = str_val[:57] + "..."
                print(f"{prefix}{key}: {str_val}")


class JsonTraceSink(TraceSink):
    """
    Sink that outputs traces as JSON lines.
    
    Useful for log aggregation systems.
    """
    
    def emit(self, trace: ExecutionTrace) -> None:
        """Print trace as JSON line."""
        try:
            # Custom serializer for datetime
            def serializer(obj: Any) -> str:
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return str(obj)
            
            print(json.dumps(trace.to_dict(), default=serializer))
            
        except Exception as e:
            print(f"[TRACE ERROR] Failed to emit JSON trace: {e}")
