"""Session management for running agents."""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AgentSession:
    """Represents a running agent session."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.utcnow()
        self.is_running = True
        self.stop_requested = False
        self._stop_event = asyncio.Event()
    
    def request_stop(self) -> None:
        """Request the agent to stop."""
        self.stop_requested = True
        self._stop_event.set()
        logger.info("Stop requested for session %s", self.session_id)
    
    def should_stop(self) -> bool:
        """Check if the agent should stop."""
        return self.stop_requested
    
    async def wait_for_stop(self, timeout: float = 0.0) -> bool:
        """Wait for stop signal with optional timeout."""
        if timeout > 0:
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout)
                return True
            except asyncio.TimeoutError:
                return False
        return self.stop_requested
    
    def mark_completed(self) -> None:
        """Mark the session as completed."""
        self.is_running = False


class SessionManager:
    """Manages active agent sessions."""
    
    _instance: Optional["SessionManager"] = None
    _sessions: Dict[str, AgentSession]
    
    def __new__(cls) -> "SessionManager":
        """Singleton pattern to ensure one session manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._sessions = {}
        return cls._instance
    
    def create_session(self) -> AgentSession:
        """Create a new agent session."""
        session_id = str(uuid.uuid4())
        session = AgentSession(session_id)
        self._sessions[session_id] = session
        logger.info("Created session %s", session_id)
        return session
    
    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)
    
    def stop_session(self, session_id: str) -> bool:
        """Stop a session by ID."""
        session = self._sessions.get(session_id)
        if session and session.is_running:
            session.request_stop()
            return True
        return False
    
    def stop_all_sessions(self) -> int:
        """Stop all running sessions."""
        count = 0
        for session in self._sessions.values():
            if session.is_running:
                session.request_stop()
                count += 1
        logger.info("Stopped %d sessions", count)
        return count
    
    def remove_session(self, session_id: str) -> None:
        """Remove a completed session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("Removed session %s", session_id)
    
    def get_active_sessions(self) -> list[str]:
        """Get list of active session IDs."""
        return [
            session_id
            for session_id, session in self._sessions.items()
            if session.is_running
        ]
    
    def cleanup_completed(self) -> int:
        """Remove all completed sessions."""
        completed = [
            session_id
            for session_id, session in self._sessions.items()
            if not session.is_running
        ]
        for session_id in completed:
            del self._sessions[session_id]
        return len(completed)


def get_session_manager() -> SessionManager:
    """Get the singleton session manager."""
    return SessionManager()
