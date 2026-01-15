"""Rate limiting configuration and utilities."""

import logging
from typing import Callable

from fastapi import Request, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from browser_agent.config import get_settings

logger = logging.getLogger(__name__)


def get_client_identifier(request: Request) -> str:
    """Get a unique identifier for the client.
    
    Uses X-Forwarded-For header if behind a proxy, otherwise uses remote address.
    Can be extended to use API keys or user IDs for authenticated requests.
    
    Args:
        request: The incoming request.
        
    Returns:
        String identifier for rate limiting.
    """
    # Check for forwarded header (when behind proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP in the chain (original client)
        return forwarded.split(",")[0].strip()
    
    # Check for API key in header (for per-key rate limiting)
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # Use a hash of the API key to avoid logging sensitive data
        return f"apikey:{hash(api_key) % 100000}"
    
    # Fall back to remote address
    return get_remote_address(request)


def create_limiter() -> Limiter:
    """Create and configure the rate limiter.
    
    Returns:
        Configured Limiter instance.
    """
    settings = get_settings()
    
    limiter = Limiter(
        key_func=get_client_identifier,
        default_limits=[settings.rate_limit_default],
        enabled=settings.rate_limit_enabled,
        storage_uri="memory://",  # Use in-memory storage (for single instance)
    )
    
    return limiter


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Handle rate limit exceeded errors.
    
    Args:
        request: The incoming request.
        exc: The rate limit exception.
        
    Returns:
        JSON response with error details.
    """
    logger.warning(
        "Rate limit exceeded for %s on %s",
        get_client_identifier(request),
        request.url.path,
    )
    
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Too many requests. Limit: {exc.detail}",
            "retry_after": getattr(exc, "retry_after", 60),
        },
        headers={
            "Retry-After": str(getattr(exc, "retry_after", 60)),
            "X-RateLimit-Limit": exc.detail,
        },
    )


# Create the global limiter instance
limiter = create_limiter()
