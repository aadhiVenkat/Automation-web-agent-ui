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

router = APIRouter(prefix="/api", tags=["agent"])
settings = get_settings()


async def event_generator(request: AgentRequest, api_key: str) -> AsyncGenerator[dict, None]:
    """Generate SSE events from the agent service.
    
    This generator yields events as they are produced by the agent,
    including logs, screenshots, and generated code.
    
    Args:
        request: The agent request.
        api_key: Resolved API key for the LLM provider.
    """
    agent_service = AgentService()
    
    try:
        async for event in agent_service.run(request, api_key):
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
    
    return EventSourceResponse(event_generator(agent_request, api_key))


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
