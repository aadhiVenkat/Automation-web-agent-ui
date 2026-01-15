"""Logging configuration for browser agent."""

import logging
import sys
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
) -> None:
    """Configure logging for the browser agent.
    
    Args:
        level: Logging level (default: INFO).
        format_string: Custom format string (optional).
    """
    if format_string is None:
        format_string = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format=format_string,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    # Set specific loggers
    logging.getLogger("browser_agent").setLevel(level)
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given module name.
    
    Args:
        name: Module name (typically __name__).
        
    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
