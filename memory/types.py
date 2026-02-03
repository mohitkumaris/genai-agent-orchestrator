"""
Memory Types

Data structures for session memory.

DESIGN RULES:
- Immutable data
- No business logic
- Session-scoped only
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass(frozen=True)
class Turn:
    """
    A single conversation turn.
    
    Represents one user ↔ assistant exchange.
    """
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_prompt_format(self) -> str:
        """Format for prompt injection."""
        prefix = "User:" if self.role == "user" else "Assistant:"
        return f"{prefix} {self.content}"


@dataclass
class SessionContext:
    """
    Session conversation context.
    
    Contains recent turns for prompt construction.
    """
    session_id: str
    turns: List[Turn] = field(default_factory=list)
    max_turns: int = 10
    
    def add_turn(self, role: str, content: str) -> None:
        """Add a turn, maintaining max size."""
        self.turns.append(Turn(role=role, content=content))
        
        # Trim oldest if exceeded
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]
    
    def to_prompt_context(self) -> str:
        """
        Format context for prompt injection.
        
        Returns:
            Formatted string of recent conversation
        """
        if not self.turns:
            return ""
        
        lines = ["[Previous conversation:]"]
        for turn in self.turns:
            lines.append(turn.to_prompt_format())
        lines.append("[Current request:]")
        
        return "\n".join(lines)
    
    def is_empty(self) -> bool:
        """Check if context has any turns."""
        return len(self.turns) == 0
    
    def clear(self) -> None:
        """Clear all turns."""
        self.turns = []
