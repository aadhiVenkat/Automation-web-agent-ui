"""Agent orchestration service - connects API to agent implementation."""

import logging
from datetime import datetime
from typing import AsyncGenerator, Optional

from browser_agent.core.agent import Agent, AgentConfig
from browser_agent.llm import create_llm_client
from browser_agent.models import AgentEvent, AgentRequest
from browser_agent.models.agent import EventType
from browser_agent.services.session import AgentSession

logger = logging.getLogger(__name__)


class AgentService:
    """Service for orchestrating browser automation agents.
    
    This service:
    - Creates and configures the agent based on API requests
    - Translates agent events to API events for SSE streaming
    - Handles error recovery and cleanup
    """

    def __init__(self) -> None:
        """Initialize the agent service."""
        pass

    async def run(
        self,
        request: AgentRequest,
        api_key: Optional[str] = None,
        session: Optional[AgentSession] = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute the agent loop and yield events.
        
        Args:
            request: The agent request containing task details and configuration.
            api_key: Resolved API key (from header, body, or environment).
            session: Optional session for stop functionality.
            
        Yields:
            AgentEvent: Events including logs, screenshots, code, and errors.
        """
        # Use provided api_key or fall back to request body (backwards compat)
        resolved_key = api_key or request.api_key
        
        if not resolved_key:
            yield AgentEvent(
                type=EventType.ERROR,
                message="API key is required. Provide via X-API-Key header or apiKey in request body.",
                timestamp=datetime.utcnow(),
            )
            return
        
        # Create LLM client
        try:
            llm_client = create_llm_client(
                provider=request.provider.value,
                api_key=resolved_key,
            )
        except Exception as e:
            yield AgentEvent(
                type=EventType.ERROR,
                message=f"Failed to initialize LLM client: {str(e)}",
                timestamp=datetime.utcnow(),
            )
            return

        # Configure agent
        # Build HTTP credentials if provided
        http_credentials = None
        if request.url_username and request.url_password:
            http_credentials = {
                "username": request.url_username,
                "password": request.url_password,
            }
        
        config = AgentConfig(
            max_steps=30,
            headless=request.headless,  # User can set to false to see browser
            screenshot_on_step=True,
            framework=request.framework,  # Pass framework for code generation
            language=request.language,    # Pass language for code generation
            use_boost_prompt=request.use_boost_prompt,  # Control task enhancement
            temperature=0.0,  # Deterministic by default
            use_structured_execution=request.use_structured_execution,  # Break down complex tasks
            verify_each_step=request.verify_each_step,  # Verify steps complete
            http_credentials=http_credentials,  # URL authentication
        )

        # Create and run agent
        agent = Agent(llm_client=llm_client, config=config)
        
        try:
            async for event in agent.run(task=request.task, url=request.url, session=session):
                # Check if stop was requested
                if session and session.should_stop():
                    yield AgentEvent(
                        type=EventType.LOG,
                        message="Stop signal received, cleaning up...",
                        timestamp=datetime.utcnow(),
                    )
                    break
                    
                yield self._convert_event(event)
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error("Agent execution error: %s\n%s", str(e), error_details)
            yield AgentEvent(
                type=EventType.ERROR,
                message=f"Agent execution error: {str(e)}",
                timestamp=datetime.utcnow(),
            )
        finally:
            # Cleanup LLM client
            if hasattr(llm_client, 'close'):
                try:
                    await llm_client.close()
                except Exception as close_error:
                    logger.warning("Error closing LLM client: %s", close_error)

    def _convert_event(self, event: dict) -> AgentEvent:
        """Convert internal agent event to API AgentEvent."""
        event_type = event.get("type", "log")
        
        if event_type == "log":
            return AgentEvent(
                type=EventType.LOG,
                message=event.get("message"),
                timestamp=datetime.utcnow(),
            )
        elif event_type == "screenshot":
            return AgentEvent(
                type=EventType.SCREENSHOT,
                screenshot=event.get("screenshot"),
                timestamp=datetime.utcnow(),
            )
        elif event_type == "code":
            return AgentEvent(
                type=EventType.CODE,
                code=event.get("code"),
                timestamp=datetime.utcnow(),
            )
        elif event_type == "tool":
            # Log tool execution as a log event
            tool_name = event.get("tool", "unknown")
            tool_args = event.get("args", {})
            return AgentEvent(
                type=EventType.LOG,
                message=f"🔧 Tool: {tool_name} - Args: {tool_args}",
                timestamp=datetime.utcnow(),
            )
        elif event_type == "boosted_prompt":
            # Show the enhanced task plan
            content = event.get("content", "")
            # Truncate for display
            preview = content[:500] + "..." if len(content) > 500 else content
            return AgentEvent(
                type=EventType.LOG,
                message=f"📋 Enhanced Task Plan:\n{preview}",
                timestamp=datetime.utcnow(),
            )
        elif event_type == "complete":
            return AgentEvent(
                type=EventType.COMPLETE,
                message=event.get("message", "Agent completed"),
                timestamp=datetime.utcnow(),
            )
        elif event_type == "error":
            return AgentEvent(
                type=EventType.ERROR,
                message=event.get("message", "Unknown error"),
                timestamp=datetime.utcnow(),
            )
        else:
            return AgentEvent(
                type=EventType.LOG,
                message=str(event),
                timestamp=datetime.utcnow(),
            )
