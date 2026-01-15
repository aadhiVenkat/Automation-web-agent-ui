"""FastAPI application entry point."""

import asyncio
import logging
import sys
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from browser_agent import __version__
from browser_agent.api import router
from browser_agent.config import get_settings
from browser_agent.logging import setup_logging
from browser_agent.ratelimit import limiter, rate_limit_exceeded_handler


# Fix for Windows + Python 3.14 asyncio subprocess issue
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Initialize logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured application instance.
    """
    settings = get_settings()
    
    app = FastAPI(
        title="Browser Agent API",
        description="""
        Browser Agent Platform API for automated browser testing and code generation.
        
        ## Features
        
        - **Agent Orchestration**: Run browser automation agents with natural language instructions
        - **Real-time Streaming**: SSE streaming of logs, screenshots, and generated code
        - **Code Generation**: Generate Playwright test code from structured test plans
        - **Multi-LLM Support**: Supports Gemini, Perplexity, and HuggingFace providers
        
        ## Usage
        
        1. Send a POST request to `/api/agent` with your task description
        2. Receive real-time updates via Server-Sent Events
        3. Get generated test code at the end of the agent run
        
        Alternatively, use `/api/generate-code` to generate code from a predefined test plan.
        """,
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    
    # Configure rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    
    # Include API routes
    app.include_router(router)
    
    logger.info("Rate limiting %s", "enabled" if settings.rate_limit_enabled else "disabled")
    
    return app


# Create application instance
app = create_app()


def run() -> None:
    """Run the application using uvicorn."""
    settings = get_settings()
    uvicorn.run(
        "browser_agent.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()
