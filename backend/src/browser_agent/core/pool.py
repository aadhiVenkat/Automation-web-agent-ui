"""Browser session pool for efficient resource management.

This module provides a pool of browser sessions that can be reused
across requests, improving performance and reducing startup latency.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from browser_agent.core.sync_browser import AsyncBrowserAdapter

logger = logging.getLogger(__name__)


@dataclass
class PooledSession:
    """A pooled browser session with metadata."""
    id: str
    browser: AsyncBrowserAdapter
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used_at: datetime = field(default_factory=datetime.utcnow)
    use_count: int = 0
    in_use: bool = False
    
    def touch(self) -> None:
        """Update last used time and increment use count."""
        self.last_used_at = datetime.utcnow()
        self.use_count += 1
    
    def age_seconds(self) -> float:
        """Get age of session in seconds."""
        return (datetime.utcnow() - self.created_at).total_seconds()
    
    def idle_seconds(self) -> float:
        """Get idle time in seconds."""
        return (datetime.utcnow() - self.last_used_at).total_seconds()


@dataclass
class PoolConfig:
    """Configuration for browser session pool."""
    min_sessions: int = 1  # Minimum sessions to keep warm
    max_sessions: int = 5  # Maximum concurrent sessions
    max_session_age: float = 300.0  # Max session age in seconds (5 min)
    max_idle_time: float = 60.0  # Max idle time before recycling (1 min)
    max_uses_per_session: int = 10  # Max uses before recycling
    cleanup_interval: float = 30.0  # Cleanup check interval in seconds
    
    # Browser settings
    headless: bool = True
    viewport_width: int = 1280
    viewport_height: int = 720
    timeout: int = 30000


class BrowserSessionPool:
    """Pool of reusable browser sessions.
    
    This pool manages browser instances to:
    - Reduce startup latency by keeping warm sessions
    - Limit resource usage with configurable max sessions
    - Automatically recycle stale sessions
    - Handle concurrent access safely
    
    Usage:
        pool = BrowserSessionPool()
        await pool.start()
        
        async with pool.acquire() as session:
            await session.browser.goto("https://example.com")
            # ... use browser
        
        await pool.shutdown()
    """
    
    _instance: Optional["BrowserSessionPool"] = None
    _lock = asyncio.Lock()
    
    def __init__(self, config: Optional[PoolConfig] = None) -> None:
        """Initialize the browser session pool."""
        self.config = config or PoolConfig()
        self._sessions: dict[str, PooledSession] = {}
        self._session_lock = asyncio.Lock()
        self._started = False
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
    
    @classmethod
    async def get_instance(cls, config: Optional[PoolConfig] = None) -> "BrowserSessionPool":
        """Get or create the singleton pool instance."""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config)
                await cls._instance.start()
            return cls._instance
    
    @classmethod
    async def shutdown_instance(cls) -> None:
        """Shutdown the singleton instance."""
        async with cls._lock:
            if cls._instance is not None:
                await cls._instance.shutdown()
                cls._instance = None
    
    async def start(self) -> None:
        """Start the pool and initialize minimum sessions."""
        if self._started:
            return
        
        logger.info("Starting browser session pool (min=%d, max=%d)", 
                   self.config.min_sessions, self.config.max_sessions)
        
        # Pre-warm minimum sessions
        for _ in range(self.config.min_sessions):
            try:
                await self._create_session()
            except Exception as e:
                logger.warning("Failed to pre-warm session: %s", e)
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._started = True
        
        logger.info("Browser session pool started with %d warm sessions", len(self._sessions))
    
    async def shutdown(self) -> None:
        """Shutdown the pool and close all sessions."""
        if not self._started:
            return
        
        logger.info("Shutting down browser session pool...")
        
        # Stop cleanup task
        self._shutdown_event.set()
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all sessions
        async with self._session_lock:
            for session_id, session in list(self._sessions.items()):
                await self._close_session(session)
            self._sessions.clear()
        
        self._started = False
        logger.info("Browser session pool shutdown complete")
    
    async def _create_session(self) -> PooledSession:
        """Create a new browser session."""
        session_id = str(uuid4())[:8]
        
        browser = AsyncBrowserAdapter(
            headless=self.config.headless,
            viewport_width=self.config.viewport_width,
            viewport_height=self.config.viewport_height,
            timeout=self.config.timeout,
        )
        
        await browser.launch()
        
        session = PooledSession(
            id=session_id,
            browser=browser,
        )
        
        async with self._session_lock:
            self._sessions[session_id] = session
        
        logger.debug("Created new browser session: %s", session_id)
        return session
    
    async def _close_session(self, session: PooledSession) -> None:
        """Close a browser session."""
        try:
            await session.browser.close()
            logger.debug("Closed browser session: %s (uses=%d, age=%.0fs)",
                        session.id, session.use_count, session.age_seconds())
        except Exception as e:
            logger.warning("Error closing session %s: %s", session.id, e)
    
    async def _cleanup_loop(self) -> None:
        """Background task to cleanup stale sessions."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self._cleanup_stale_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in cleanup loop: %s", e)
    
    async def _cleanup_stale_sessions(self) -> None:
        """Remove stale sessions and ensure minimum pool size."""
        async with self._session_lock:
            sessions_to_remove = []
            
            for session_id, session in self._sessions.items():
                if session.in_use:
                    continue
                
                # Check if session should be recycled
                should_recycle = (
                    session.age_seconds() > self.config.max_session_age or
                    session.idle_seconds() > self.config.max_idle_time or
                    session.use_count >= self.config.max_uses_per_session
                )
                
                if should_recycle:
                    sessions_to_remove.append(session_id)
            
            # Keep at least min_sessions
            available_count = sum(1 for s in self._sessions.values() if not s.in_use)
            available_count -= len(sessions_to_remove)
            
            # Only remove if we'll still have min_sessions available
            for session_id in sessions_to_remove:
                if available_count >= self.config.min_sessions:
                    session = self._sessions.pop(session_id)
                    await self._close_session(session)
                else:
                    break
        
        # Ensure minimum sessions exist
        current_count = len(self._sessions)
        if current_count < self.config.min_sessions:
            for _ in range(self.config.min_sessions - current_count):
                try:
                    await self._create_session()
                except Exception as e:
                    logger.warning("Failed to create replacement session: %s", e)
    
    async def acquire(self) -> "BrowserSessionContext":
        """Acquire a browser session from the pool.
        
        Returns a context manager that automatically releases the session.
        
        Usage:
            async with pool.acquire() as session:
                await session.browser.goto("https://example.com")
        """
        session = await self._get_available_session()
        return BrowserSessionContext(self, session)
    
    async def _get_available_session(self) -> PooledSession:
        """Get an available session from the pool or create a new one."""
        async with self._session_lock:
            # Look for an available session
            for session in self._sessions.values():
                if not session.in_use:
                    session.in_use = True
                    session.touch()
                    logger.debug("Acquired existing session: %s (uses=%d)",
                               session.id, session.use_count)
                    return session
            
            # Check if we can create a new session
            if len(self._sessions) < self.config.max_sessions:
                # Release lock while creating session
                pass
            else:
                raise RuntimeError(
                    f"Browser session pool exhausted (max={self.config.max_sessions}). "
                    "Try again later or increase max_sessions."
                )
        
        # Create new session outside lock
        session = await self._create_session()
        session.in_use = True
        session.touch()
        return session
    
    async def release(self, session: PooledSession) -> None:
        """Release a session back to the pool."""
        async with self._session_lock:
            if session.id in self._sessions:
                session.in_use = False
                logger.debug("Released session: %s", session.id)
                
                # Reset browser state for next use
                try:
                    # Navigate to blank page to clear state
                    await session.browser.goto("about:blank", wait_until="domcontentloaded")
                except Exception as e:
                    logger.warning("Failed to reset session %s: %s", session.id, e)
                    # Mark session for removal on next cleanup
                    session.use_count = self.config.max_uses_per_session
    
    def stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        total = len(self._sessions)
        in_use = sum(1 for s in self._sessions.values() if s.in_use)
        available = total - in_use
        
        return {
            "total_sessions": total,
            "in_use": in_use,
            "available": available,
            "min_sessions": self.config.min_sessions,
            "max_sessions": self.config.max_sessions,
            "sessions": [
                {
                    "id": s.id,
                    "in_use": s.in_use,
                    "use_count": s.use_count,
                    "age_seconds": s.age_seconds(),
                    "idle_seconds": s.idle_seconds(),
                }
                for s in self._sessions.values()
            ]
        }


class BrowserSessionContext:
    """Context manager for acquired browser sessions."""
    
    def __init__(self, pool: BrowserSessionPool, session: PooledSession) -> None:
        self.pool = pool
        self.session = session
    
    @property
    def browser(self) -> AsyncBrowserAdapter:
        """Get the browser adapter."""
        return self.session.browser
    
    async def __aenter__(self) -> "BrowserSessionContext":
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.pool.release(self.session)


# Convenience function for one-off session usage
async def get_browser_session(
    headless: bool = True,
    use_pool: bool = True,
) -> AsyncBrowserAdapter:
    """Get a browser session, optionally from the pool.
    
    Args:
        headless: Run browser in headless mode
        use_pool: If True, use the session pool; otherwise create standalone session
    
    Returns:
        AsyncBrowserAdapter: Browser adapter instance
    """
    if use_pool:
        pool = await BrowserSessionPool.get_instance(PoolConfig(headless=headless))
        context = await pool.acquire()
        return context.browser
    else:
        browser = AsyncBrowserAdapter(headless=headless)
        await browser.launch()
        return browser
