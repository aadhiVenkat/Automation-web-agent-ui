"""Retry utilities for LLM API calls."""

import logging
from functools import wraps
from typing import Callable, TypeVar

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger(__name__)

# Type variable for generic function return type
T = TypeVar('T')

# Exceptions that should trigger a retry
RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.HTTPStatusError,  # For 429 and 5xx errors
)


def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 10,
) -> Callable:
    """Decorator to add retry logic with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts.
        min_wait: Minimum wait time between retries in seconds.
        max_wait: Maximum wait time between retries in seconds.
        
    Returns:
        Decorated function with retry logic.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def is_retryable_error(exception: Exception) -> bool:
    """Check if an exception should trigger a retry.
    
    Args:
        exception: The exception to check.
        
    Returns:
        True if the exception is retryable.
    """
    return isinstance(exception, RETRYABLE_EXCEPTIONS)
