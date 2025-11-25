"""
Logging Configuration Module

This module sets up structured logging using structlog.
It provides consistent logging across the application with JSON formatting.

Key Features:
- Structured logging with context
- JSON output for log aggregation
- Request ID tracking
- Performance logging
- Different log levels per environment

Usage:
    from app.core.logging import get_logger
    
    logger = get_logger(__name__)
    logger.info("Operation completed", user_id=123, duration_ms=45)
"""

import logging
import sys
from typing import Any, Dict
import structlog
from app.core.config import settings


def setup_logging() -> None:
    """
    Configure structured logging for the application.
    
    This function sets up structlog with appropriate processors
    for development and production environments.
    """
    
    # Determine log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Structlog processors for log formatting
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add appropriate renderer based on format setting
    if settings.LOG_FORMAT == "json" or settings.is_production:
        # JSON formatting for production (easier to parse in log aggregation)
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Console-friendly formatting for development
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__ of the module)
        
    Returns:
        Configured structlog logger
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("User logged in", user_id=123, ip="192.168.1.1")
    """
    return structlog.get_logger(name)


class RequestLogMiddleware:
    """
    Middleware to log HTTP requests and responses.
    
    This middleware adds request/response logging with timing information.
    It's useful for monitoring API performance and debugging.
    """
    
    def __init__(self, app: Any):
        self.app = app
        self.logger = get_logger("request")
    
    async def __call__(self, scope: Dict[str, Any], receive: Any, send: Any) -> None:
        """
        Process HTTP request/response with logging.
        
        Args:
            scope: ASGI scope dictionary
            receive: ASGI receive channel
            send: ASGI send channel
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        import time
        start_time = time.time()
        
        # Log request
        self.logger.info(
            "Request started",
            method=scope["method"],
            path=scope["path"],
            client=scope.get("client"),
        )
        
        # Process request
        try:
            await self.app(scope, receive, send)
        finally:
            # Log response with timing
            duration_ms = (time.time() - start_time) * 1000
            self.logger.info(
                "Request completed",
                method=scope["method"],
                path=scope["path"],
                duration_ms=round(duration_ms, 2),
            )


# Initialize logging on module import
setup_logging()
