"""Security utilities for API authentication."""

import logging
from typing import Optional

from fastapi import Header, HTTPException, Request, status

from browser_agent.config import get_settings
from browser_agent.models.agent import LLMProvider

logger = logging.getLogger(__name__)


class APIKeyError(HTTPException):
    """Exception for API key related errors."""
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "X-API-Key"},
        )


def get_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key", description="API key for the LLM provider"),
) -> Optional[str]:
    """Extract API key from request header.
    
    The API key can be provided in the X-API-Key header.
    If not provided in header, it may be in the request body (for backwards compatibility).
    
    Args:
        request: The FastAPI request object.
        x_api_key: API key from header.
        
    Returns:
        The API key if found, None otherwise.
    """
    if x_api_key:
        return x_api_key
    return None


def resolve_api_key(
    header_api_key: Optional[str],
    body_api_key: Optional[str],
    provider: LLMProvider,
) -> str:
    """Resolve the API key from header, body, or environment.
    
    Priority order:
    1. Header (X-API-Key) - most secure
    2. Request body (apiKey) - backwards compatibility
    3. Environment variable - server default
    
    Args:
        header_api_key: API key from X-API-Key header.
        body_api_key: API key from request body.
        provider: The LLM provider to use.
        
    Returns:
        The resolved API key.
        
    Raises:
        APIKeyError: If no API key is available.
    """
    settings = get_settings()
    
    # Priority 1: Header
    if header_api_key:
        logger.debug("Using API key from header")
        return header_api_key
    
    # Priority 2: Body (backwards compatibility, but log warning)
    if body_api_key:
        logger.debug("Using API key from request body (consider using X-API-Key header instead)")
        return body_api_key
    
    # Priority 3: Environment variable
    env_key = None
    if provider == LLMProvider.GEMINI:
        env_key = settings.gemini_api_key
    elif provider == LLMProvider.PERPLEXITY:
        env_key = settings.perplexity_api_key
    elif provider == LLMProvider.HUGGINGFACE:
        env_key = settings.huggingface_api_key
    
    if env_key:
        logger.debug("Using API key from environment")
        return env_key
    
    # No API key found
    raise APIKeyError(
        f"API key required for {provider.value}. "
        f"Provide via X-API-Key header, apiKey in body, or set {provider.value.upper()}_API_KEY environment variable."
    )


def mask_api_key(api_key: str) -> str:
    """Mask an API key for safe logging.
    
    Shows only first 4 and last 4 characters.
    
    Args:
        api_key: The API key to mask.
        
    Returns:
        Masked API key string.
    """
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}...{api_key[-4:]}"
