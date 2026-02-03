"""
Session Store

In-memory session-scoped conversation storage.

DESIGN RULES:
- No long-term persistence
- No cross-session sharing
- Read-only for prompt construction
- Automatically cleared on session end
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from threading import Lock

from memory.types import SessionContext


class SessionStore:
    """
    In-memory session store.
    
    Stores recent conversation turns keyed by session_id.
    NOT persistent - data lives only in process memory.
    
    Thread-safe for concurrent access.
    """
    
    # Default max turns per session
    DEFAULT_MAX_TURNS = 10
    
    # Session timeout (auto-clear after inactivity)
    SESSION_TIMEOUT_MINUTES = 30
    
    def __init__(self, max_turns: int = DEFAULT_MAX_TURNS):
        """
        Initialize session store.
        
        Args:
            max_turns: Maximum turns to keep per session
        """
        self._sessions: Dict[str, SessionContext] = {}
        self._last_access: Dict[str, datetime] = {}
        self._max_turns = max_turns
        self._lock = Lock()
    
    def get_context(self, session_id: str) -> SessionContext:
        """
        Get or create session context.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            SessionContext for the session
        """
        with self._lock:
            self._cleanup_expired()
            
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionContext(
                    session_id=session_id,
                    max_turns=self._max_turns,
                )
            
            self._last_access[session_id] = datetime.now()
            return self._sessions[session_id]
    
    def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """
        Add a conversation turn to session.
        
        Args:
            session_id: Session identifier
            role: "user" or "assistant"
            content: Turn content
        """
        context = self.get_context(session_id)
        context.add_turn(role, content)
    
    def get_prompt_context(self, session_id: str) -> str:
        """
        Get formatted context for prompt injection.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Formatted context string, empty if new session
        """
        context = self.get_context(session_id)
        return context.to_prompt_context()
    
    def clear_session(self, session_id: str) -> None:
        """
        Clear a session's memory.
        
        Args:
            session_id: Session to clear
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
            if session_id in self._last_access:
                del self._last_access[session_id]
    
    def _cleanup_expired(self) -> None:
        """Remove expired sessions (internal)."""
        cutoff = datetime.now() - timedelta(minutes=self.SESSION_TIMEOUT_MINUTES)
        expired = [
            sid for sid, last in self._last_access.items()
            if last < cutoff
        ]
        for sid in expired:
            del self._sessions[sid]
            del self._last_access[sid]
    
    def session_count(self) -> int:
        """Get count of active sessions."""
        with self._lock:
            self._cleanup_expired()
            return len(self._sessions)


# Global singleton (process-scoped)
_global_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """Get the global session store singleton."""
    global _global_store
    if _global_store is None:
        _global_store = SessionStore()
    return _global_store
