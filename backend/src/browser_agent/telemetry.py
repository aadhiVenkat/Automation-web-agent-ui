"""Telemetry and observability for agent operations.

This module provides structured logging, metrics collection, and tracing
for debugging and monitoring agent performance.
"""

import asyncio
import functools
import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of telemetry events."""
    AGENT_START = "agent.start"
    AGENT_STEP = "agent.step"
    AGENT_END = "agent.end"
    AGENT_ERROR = "agent.error"
    
    TOOL_START = "tool.start"
    TOOL_END = "tool.end"
    TOOL_ERROR = "tool.error"
    
    LLM_REQUEST = "llm.request"
    LLM_RESPONSE = "llm.response"
    LLM_ERROR = "llm.error"
    
    BROWSER_ACTION = "browser.action"
    BROWSER_ERROR = "browser.error"
    
    RECOVERY_ATTEMPT = "recovery.attempt"
    RECOVERY_SUCCESS = "recovery.success"
    RECOVERY_FAILED = "recovery.failed"


@dataclass
class TelemetryEvent:
    """A telemetry event for tracking and debugging."""
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    parent_span_id: Optional[str] = None
    
    # Event-specific data
    name: str = ""
    duration_ms: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Token usage (for LLM events)
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for logging/export."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


@dataclass
class AgentMetrics:
    """Aggregated metrics for an agent run."""
    trace_id: str
    task: str
    url: str
    
    # Timing
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    total_duration_ms: float = 0.0
    
    # Step counts
    total_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    
    # Tool usage
    tool_calls: dict[str, int] = field(default_factory=dict)
    tool_errors: dict[str, int] = field(default_factory=dict)
    
    # LLM usage
    llm_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    
    # Recovery
    recovery_attempts: int = 0
    recovery_successes: int = 0
    
    # Final state
    completed: bool = False
    success: Optional[bool] = None
    error: Optional[str] = None
    
    def record_step(self, success: bool, tool_name: Optional[str] = None) -> None:
        """Record a step execution."""
        self.total_steps += 1
        if success:
            self.successful_steps += 1
        else:
            self.failed_steps += 1
        
        if tool_name:
            self.tool_calls[tool_name] = self.tool_calls.get(tool_name, 0) + 1
            if not success:
                self.tool_errors[tool_name] = self.tool_errors.get(tool_name, 0) + 1
    
    def record_llm_call(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        """Record an LLM API call."""
        self.llm_calls += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
    
    def record_recovery(self, success: bool) -> None:
        """Record a recovery attempt."""
        self.recovery_attempts += 1
        if success:
            self.recovery_successes += 1
    
    def finalize(self, success: Optional[bool] = None, error: Optional[str] = None) -> None:
        """Finalize metrics at the end of agent run."""
        self.end_time = datetime.utcnow()
        self.total_duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.completed = True
        self.success = success
        self.error = error
    
    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "trace_id": self.trace_id,
            "task": self.task,
            "url": self.url,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration_ms": self.total_duration_ms,
            "total_steps": self.total_steps,
            "successful_steps": self.successful_steps,
            "failed_steps": self.failed_steps,
            "tool_calls": self.tool_calls,
            "tool_errors": self.tool_errors,
            "llm_calls": self.llm_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "recovery_attempts": self.recovery_attempts,
            "recovery_successes": self.recovery_successes,
            "completed": self.completed,
            "success": self.success,
            "error": self.error,
        }
    
    def summary(self) -> str:
        """Generate a human-readable summary."""
        success_rate = (self.successful_steps / self.total_steps * 100) if self.total_steps > 0 else 0
        return (
            f"Agent Run Summary (trace_id={self.trace_id}):\n"
            f"  Task: {self.task[:50]}...\n"
            f"  Duration: {self.total_duration_ms:.0f}ms\n"
            f"  Steps: {self.successful_steps}/{self.total_steps} ({success_rate:.0f}% success)\n"
            f"  LLM Calls: {self.llm_calls} ({self.total_input_tokens} in, {self.total_output_tokens} out tokens)\n"
            f"  Recoveries: {self.recovery_successes}/{self.recovery_attempts}\n"
            f"  Result: {'Success' if self.success else 'Failed' if self.success is False else 'Unknown'}"
        )


class TelemetryCollector:
    """Collects and manages telemetry events for an agent run."""
    
    def __init__(self, task: str, url: str) -> None:
        """Initialize telemetry collector."""
        self.trace_id = str(uuid.uuid4())[:8]
        self.events: list[TelemetryEvent] = []
        self.metrics = AgentMetrics(trace_id=self.trace_id, task=task, url=url)
        self._span_stack: list[str] = []  # Stack for nested spans
        
        # Log start event
        self.record_event(
            EventType.AGENT_START,
            name="agent_run",
            metadata={"task": task, "url": url}
        )
    
    @property
    def current_span_id(self) -> Optional[str]:
        """Get the current span ID (top of stack)."""
        return self._span_stack[-1] if self._span_stack else None
    
    def record_event(
        self,
        event_type: EventType,
        name: str = "",
        duration_ms: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
    ) -> TelemetryEvent:
        """Record a telemetry event."""
        event = TelemetryEvent(
            event_type=event_type,
            trace_id=self.trace_id,
            parent_span_id=self.current_span_id,
            name=name,
            duration_ms=duration_ms,
            success=success,
            error=error,
            metadata=metadata or {},
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        
        self.events.append(event)
        
        # Log the event
        log_level = logging.DEBUG if success else logging.WARNING
        logger.log(
            log_level,
            "[%s] %s.%s (%.0fms) %s",
            self.trace_id,
            event_type.value,
            name,
            duration_ms or 0,
            f"error={error}" if error else ""
        )
        
        return event
    
    @contextmanager
    def span(self, name: str, event_type: EventType = EventType.AGENT_STEP):
        """Context manager for tracking a span of execution."""
        span_id = str(uuid.uuid4())[:8]
        self._span_stack.append(span_id)
        start_time = time.perf_counter()
        
        error: Optional[str] = None
        success = True
        
        try:
            yield span_id
        except Exception as e:
            error = str(e)
            success = False
            raise
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._span_stack.pop()
            
            self.record_event(
                event_type=event_type,
                name=name,
                duration_ms=duration_ms,
                success=success,
                error=error,
            )
    
    def record_tool_execution(
        self,
        tool_name: str,
        duration_ms: float,
        success: bool,
        error: Optional[str] = None,
        args: Optional[dict] = None,
    ) -> None:
        """Record a tool execution."""
        self.record_event(
            EventType.TOOL_END,
            name=tool_name,
            duration_ms=duration_ms,
            success=success,
            error=error,
            metadata={"args": args} if args else {},
        )
        self.metrics.record_step(success, tool_name)
    
    def record_llm_call(
        self,
        duration_ms: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Record an LLM API call."""
        self.record_event(
            EventType.LLM_RESPONSE,
            name="llm_chat",
            duration_ms=duration_ms,
            success=success,
            error=error,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        self.metrics.record_llm_call(input_tokens, output_tokens)
    
    def record_recovery(
        self,
        strategy: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Record a recovery attempt."""
        event_type = EventType.RECOVERY_SUCCESS if success else EventType.RECOVERY_FAILED
        self.record_event(
            event_type,
            name=strategy,
            success=success,
            error=error,
        )
        self.metrics.record_recovery(success)
    
    def finalize(self, success: Optional[bool] = None, error: Optional[str] = None) -> AgentMetrics:
        """Finalize telemetry collection."""
        self.metrics.finalize(success, error)
        
        self.record_event(
            EventType.AGENT_END,
            name="agent_run",
            duration_ms=self.metrics.total_duration_ms,
            success=success if success is not None else True,
            error=error,
            metadata=self.metrics.to_dict(),
        )
        
        # Log summary
        logger.info(self.metrics.summary())
        
        return self.metrics
    
    def get_events(self) -> list[dict[str, Any]]:
        """Get all events as dictionaries."""
        return [e.to_dict() for e in self.events]


# Decorator for timing function execution
F = TypeVar('F', bound=Callable[..., Any])


def trace_execution(event_type: EventType = EventType.AGENT_STEP):
    """Decorator to trace function execution with telemetry."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            error = None
            success = True
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                error = str(e)
                success = False
                raise
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.debug(
                    "[trace] %s completed in %.0fms (success=%s)",
                    func.__name__,
                    duration_ms,
                    success
                )
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            error = None
            success = True
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = str(e)
                success = False
                raise
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.debug(
                    "[trace] %s completed in %.0fms (success=%s)",
                    func.__name__,
                    duration_ms,
                    success
                )
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore
    
    return decorator
