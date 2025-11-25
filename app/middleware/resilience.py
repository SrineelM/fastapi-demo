"""
Resilience Middleware Module

Implements resilience patterns including:
- Circuit breaker
- Rate limiting (general, auth, upload endpoints)
- Request timeout
- Retry logic
- Metrics tracking

These patterns improve API reliability and protect against cascading failures.

Usage:
    from app.middleware.resilience import (
        RateLimitMiddleware,
        TimeoutMiddleware
    )
"""

import time
import asyncio
from typing import Callable, Dict, Any, Deque
from datetime import datetime, timedelta
from collections import deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import HTTPException, status
from app.core.logging import get_logger
from app.core.config import get_cached_settings

logger = get_logger(__name__)


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents repeated calls to failing services. States:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Failure threshold exceeded, requests fail immediately
    - HALF_OPEN: Testing if service recovered
    
    Example:
        >>> breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        >>> async with breaker:
        >>>     result = await external_service_call()
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting half-open
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        logger.info(
            "Circuit breaker initialized",
            failure_threshold=failure_threshold,
            timeout=timeout
        )
    
    async def __aenter__(self) -> "CircuitBreaker":
        """Context manager entry."""
        if self.state == "OPEN":
            # Check if timeout has elapsed
            if (self.last_failure_time and 
                time.time() - self.last_failure_time >= self.timeout):
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker state: HALF_OPEN")
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Service temporarily unavailable (circuit breaker open)"
                )
        
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Context manager exit with exception handling."""
        if exc_type is None:
            # Success
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info("Circuit breaker recovered: CLOSED")
            return False
        
        if issubclass(exc_type, self.expected_exception):
            # Failure
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(
                    "Circuit breaker opened",
                    failures=self.failure_count,
                    timeout=self.timeout
                )
            
            logger.debug(
                "Circuit breaker failure recorded",
                failures=self.failure_count,
                state=self.state
            )
        
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Advanced rate limiting middleware with endpoint-specific limits.
    
    Features:
    - Sliding window algorithm
    - Per-IP client tracking
    - Endpoint-specific rate limits (auth, upload, general)
    - Configurable limits from settings
    
    Example:
        >>> app.add_middleware(RateLimitMiddleware)
    """
    
    def __init__(self, app: Any):
        """Initialize rate limiter with settings from config."""
        super().__init__(app)
        self.settings = get_cached_settings()
        
        # Store request timestamps per client
        # Format: {client_ip: deque([timestamp1, timestamp2, ...])}
        self.client_requests: Dict[str, Deque[float]] = {}
        
        logger.info(
            "Rate limiter initialized",
            rate_limit_enabled=self.settings.RATE_LIMIT_ENABLED,
            general_limit=f"{self.settings.RATE_LIMIT_REQUESTS}/{self.settings.RATE_LIMIT_WINDOW_SECONDS}s",
            auth_limit=f"{self.settings.AUTH_RATE_LIMIT_REQUESTS}/{self.settings.AUTH_RATE_LIMIT_WINDOW_SECONDS}s",
            upload_limit=f"{self.settings.UPLOAD_RATE_LIMIT_REQUESTS}/{self.settings.UPLOAD_RATE_LIMIT_WINDOW_SECONDS}s"
        )
    
    def _get_limit_for_endpoint(self, path: str) -> tuple[int, int]:
        """
        Get rate limit (requests, window_seconds) for endpoint.
        
        Args:
            path: Request path
            
        Returns:
            Tuple of (max_requests, window_seconds)
        """
        # Auth endpoints: stricter limit
        if path.startswith("/api/v1/security"):
            return (
                self.settings.AUTH_RATE_LIMIT_REQUESTS,
                self.settings.AUTH_RATE_LIMIT_WINDOW_SECONDS
            )
        
        # Upload endpoints: stricter limit
        if path.startswith("/api/v1/files"):
            return (
                self.settings.UPLOAD_RATE_LIMIT_REQUESTS,
                self.settings.UPLOAD_RATE_LIMIT_WINDOW_SECONDS
            )
        
        # General endpoints
        return (
            self.settings.RATE_LIMIT_REQUESTS,
            self.settings.RATE_LIMIT_WINDOW_SECONDS
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler
            
        Returns:
            HTTP response or 429 Too Many Requests
        """
        # Check if rate limiting is enabled
        if not self.settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Get limit for this endpoint
        max_requests, window_seconds = self._get_limit_for_endpoint(request.url.path)
        
        # Initialize client request queue if needed
        if client_ip not in self.client_requests:
            self.client_requests[client_ip] = deque()
        
        # Current time
        now = time.time()
        
        # Remove old requests outside the window
        client_queue = self.client_requests[client_ip]
        while client_queue and client_queue[0] < now - window_seconds:
            client_queue.popleft()
        
        # Check if rate limit exceeded
        if len(client_queue) >= max_requests:
            oldest_request = client_queue[0]
            retry_after = int(oldest_request + window_seconds - now) + 1
            
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                path=request.url.path,
                requests=len(client_queue),
                limit=max_requests,
                window_seconds=window_seconds,
                retry_after=retry_after
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Max {max_requests} requests per {window_seconds} seconds",
                    "retry_after_seconds": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )
        
        # Add current request timestamp
        client_queue.append(now)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, max_requests - len(client_queue)))
        response.headers["X-RateLimit-Reset"] = str(int(now + window_seconds))
        
        return response


class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    Request timeout middleware.
    
    Cancels requests that exceed the specified timeout to prevent
    resource exhaustion from slow operations.
    
    Example:
        >>> app.add_middleware(TimeoutMiddleware, timeout=30)
    """
    
    def __init__(self, app: Any, timeout: int = 30):
        """
        Initialize timeout middleware.
        
        Args:
            app: ASGI application
            timeout: Request timeout in seconds
        """
        super().__init__(app)
        self.timeout = timeout
        
        logger.info("Timeout middleware initialized", timeout=timeout)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with timeout.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler
            
        Returns:
            HTTP response or 504 Gateway Timeout
        """
        try:
            # Execute request with timeout
            response = await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout
            )
            return response
        
        except asyncio.TimeoutError:
            logger.error(
                "Request timeout",
                path=request.url.path,
                method=request.method,
                timeout=self.timeout
            )
            
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "error": "request_timeout",
                    "message": f"Request exceeded {self.timeout} seconds timeout",
                    "path": request.url.path
                }
            )


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect request metrics.
    
    Tracks request counts, response times, and status codes
    for monitoring and observability.
    
    Example:
        >>> app.add_middleware(MetricsMiddleware)
    """
    
    def __init__(self, app: Any):
        """Initialize metrics middleware."""
        super().__init__(app)
        
        # Metrics storage
        self.metrics = {
            "total_requests": 0,
            "total_errors": 0,
            "response_times": deque(maxlen=1000),  # Keep last 1000
            "status_codes": {},
            "endpoints": {}
        }
        
        logger.info("Metrics middleware initialized")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and collect metrics.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler
            
        Returns:
            HTTP response
        """
        # Record request
        start_time = time.time()
        self.metrics["total_requests"] += 1
        
        # Get endpoint path
        path = request.url.path
        
        try:
            # Process request
            response = await call_next(request)
            
            # Record response time
            duration = time.time() - start_time
            self.metrics["response_times"].append(duration)
            
            # Record status code
            status_code = response.status_code
            self.metrics["status_codes"][status_code] = (
                self.metrics["status_codes"].get(status_code, 0) + 1
            )
            
            # Record endpoint metrics
            if path not in self.metrics["endpoints"]:
                self.metrics["endpoints"][path] = {
                    "count": 0,
                    "avg_response_time": 0.0
                }
            
            endpoint_data = self.metrics["endpoints"][path]
            endpoint_data["count"] += 1
            # Update running average
            n = endpoint_data["count"]
            endpoint_data["avg_response_time"] = (
                (endpoint_data["avg_response_time"] * (n - 1) + duration) / n
            )
            
            # Track errors
            if status_code >= 400:
                self.metrics["total_errors"] += 1
            
            # Add custom metrics header
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
            
            return response
        
        except Exception as e:
            self.metrics["total_errors"] += 1
            logger.error("Request processing error", error=str(e), path=path)
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get collected metrics.
        
        Returns:
            Dictionary with metrics data
        """
        response_times = list(self.metrics["response_times"])
        
        return {
            "total_requests": self.metrics["total_requests"],
            "total_errors": self.metrics["total_errors"],
            "error_rate": (
                self.metrics["total_errors"] / self.metrics["total_requests"]
                if self.metrics["total_requests"] > 0 else 0.0
            ),
            "avg_response_time": (
                sum(response_times) / len(response_times)
                if response_times else 0.0
            ),
            "status_codes": dict(self.metrics["status_codes"]),
            "top_endpoints": sorted(
                [
                    {
                        "path": path,
                        "count": data["count"],
                        "avg_response_time": data["avg_response_time"]
                    }
                    for path, data in self.metrics["endpoints"].items()
                ],
                key=lambda x: x["count"],
                reverse=True
            )[:10]
        }
