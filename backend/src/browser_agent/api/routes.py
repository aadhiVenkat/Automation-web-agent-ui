"""API routes for the Browser Agent Platform."""

import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from browser_agent.config import get_settings
from browser_agent.models import AgentEvent, AgentRequest, CodeGenRequest, CodeGenResponse
from browser_agent.models.agent import EventType
from browser_agent.ratelimit import limiter
from browser_agent.security import get_api_key, resolve_api_key
from browser_agent.services.agent import AgentService
from browser_agent.services.codegen import CodeGenService
from browser_agent.services.session import get_session_manager, AgentSession

router = APIRouter(prefix="/api", tags=["agent"])
settings = get_settings()


async def event_generator(request: AgentRequest, api_key: str, session: AgentSession) -> AsyncGenerator[dict, None]:
    """Generate SSE events from the agent service.
    
    This generator yields events as they are produced by the agent,
    including logs, screenshots, and generated code.
    
    Args:
        request: The agent request.
        api_key: Resolved API key for the LLM provider.
        session: The agent session for tracking and stop functionality.
    """
    agent_service = AgentService()
    session_manager = get_session_manager()
    
    # Send session ID as first event so frontend can track it
    yield {
        "event": "session",
        "data": json.dumps({"session_id": session.session_id}),
    }
    
    try:
        async for event in agent_service.run(request, api_key, session):
            # Check if stop was requested
            if session.should_stop():
                stop_event = AgentEvent(
                    type=EventType.COMPLETE,
                    message="Agent stopped by user",
                    timestamp=datetime.utcnow(),
                )
                yield {
                    "event": "complete",
                    "data": stop_event.model_dump_json(),
                }
                break
            
            yield {
                "event": event.type.value,
                "data": event.model_dump_json(),
            }
    except Exception as e:
        error_event = AgentEvent(
            type=EventType.ERROR,
            message=f"Agent error: {str(e)}",
            timestamp=datetime.utcnow(),
        )
        yield {
            "event": "error",
            "data": error_event.model_dump_json(),
        }
    finally:
        session.mark_completed()
        # Cleanup after a short delay to allow any pending responses
        await asyncio.sleep(1)
        session_manager.remove_session(session.session_id)


@router.post(
    "/agent",
    response_class=EventSourceResponse,
    summary="Run browser automation agent",
    description="""
    Orchestrate a browser automation agent that:
    - Navigates to the target URL
    - Uses LLM to plan and execute steps
    - Streams real-time logs, screenshots, and generated code
    
    ## Authentication
    
    API key can be provided via:
    1. **X-API-Key header** (recommended, most secure)
    2. **apiKey in request body** (backwards compatible)
    3. **Environment variable** (server default)
    
    Returns Server-Sent Events (SSE) with event types:
    - `log`: Progress messages
    - `screenshot`: Base64-encoded screenshots
    - `code`: Generated test code
    - `error`: Error messages
    - `complete`: Agent finished
    
    **Rate Limited**: 5 requests per minute per IP
    """,
    responses={
        200: {
            "description": "SSE stream of agent events",
            "content": {
                "text/event-stream": {
                    "example": 'event: log\ndata: {"type": "log", "message": "Navigating to URL..."}\n\n'
                }
            },
        },
        401: {"description": "API key missing or invalid"},
        422: {"description": "Validation error"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(settings.rate_limit_agent)
async def run_agent(
    request: Request,
    agent_request: AgentRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key", description="API key for the LLM provider (recommended)"),
) -> EventSourceResponse:
    """Execute browser automation agent with streaming output.
    
    The agent orchestrates browser actions based on natural language instructions,
    streaming progress events, screenshots, and generated code in real-time.
    """
    # Resolve API key from header, body, or environment
    api_key = resolve_api_key(x_api_key, agent_request.api_key, agent_request.provider)
    
    # Create a session for this agent run
    session_manager = get_session_manager()
    session = session_manager.create_session()
    
    return EventSourceResponse(event_generator(agent_request, api_key, session))


@router.post(
    "/agent/stop/{session_id}",
    summary="Stop a running agent",
    description="""
    Stop a running browser automation agent by session ID.
    
    The session ID is provided in the first SSE event when starting an agent.
    This will gracefully stop the agent and close the browser.
    """,
    responses={
        200: {"description": "Agent stop requested successfully"},
        404: {"description": "Session not found or already completed"},
    },
)
async def stop_agent(session_id: str) -> dict:
    """Stop a running agent by session ID."""
    session_manager = get_session_manager()
    
    if session_manager.stop_session(session_id):
        return {
            "status": "stopping",
            "session_id": session_id,
            "message": "Agent stop requested",
        }
    
    raise HTTPException(
        status_code=404,
        detail=f"Session {session_id} not found or already completed",
    )


@router.post(
    "/agent/stop-all",
    summary="Stop all running agents",
    description="Stop all currently running browser automation agents.",
    responses={
        200: {"description": "All agents stopped"},
    },
)
async def stop_all_agents() -> dict:
    """Stop all running agents."""
    session_manager = get_session_manager()
    count = session_manager.stop_all_sessions()
    
    return {
        "status": "success",
        "stopped_count": count,
        "message": f"Requested stop for {count} running agent(s)",
    }


@router.get(
    "/agent/sessions",
    summary="List active agent sessions",
    description="Get a list of all currently active agent session IDs.",
    responses={
        200: {"description": "List of active sessions"},
    },
)
async def list_sessions() -> dict:
    """List all active agent sessions."""
    session_manager = get_session_manager()
    sessions = session_manager.get_active_sessions()
    
    return {
        "active_sessions": sessions,
        "count": len(sessions),
    }


@router.post(
    "/generate-code",
    response_model=CodeGenResponse,
    summary="Generate test code from test plan",
    description="""
    Generate executable Playwright test code from a structured test plan.
    
    Supports:
    - TypeScript, Python, and JavaScript output
    - Playwright framework
    - Common actions: navigate, click, fill, wait, assert
    
    **Rate Limited**: 20 requests per minute per IP
    """,
    responses={
        200: {
            "description": "Generated test code",
            "content": {
                "application/json": {
                    "example": {
                        "code": "import { test, expect } from '@playwright/test';...",
                        "filename": "test-example.spec.ts",
                    }
                }
            },
        },
        422: {"description": "Validation error"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(settings.rate_limit_codegen)
async def generate_code(request: Request, codegen_request: CodeGenRequest) -> CodeGenResponse:
    """Generate test code from a structured test plan.
    
    Takes a list of test steps and generates executable Playwright test code
    in the specified programming language.
    """
    codegen_service = CodeGenService()
    return await codegen_service.generate(codegen_request)


@router.get(
    "/health",
    summary="Health check endpoint",
    description="Returns the health status of the API.",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {"application/json": {"example": {"status": "healthy", "version": "0.1.0"}}},
        },
    },
)
async def health_check() -> dict:
    """Check API health status."""
    from browser_agent import __version__

    return {
        "status": "healthy",
        "version": __version__,
        "timestamp": datetime.utcnow().isoformat(),
    }
