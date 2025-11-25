"""
Security Headers Middleware Module

Adds security-related HTTP response headers to protect against common vulnerabilities.

Headers added:
- Strict-Transport-Security (HSTS): Force HTTPS
- X-Content-Type-Options: Prevent MIME sniffing
- X-Frame-Options: Prevent clickjacking
- X-XSS-Protection: Enable XSS protection
- Content-Security-Policy: Control resource loading
- Referrer-Policy: Control referrer information
- Permissions-Policy: Control browser features
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_cached_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    
    Best practices:
    - HSTS: Force HTTPS for future connections
    - X-Content-Type-Options: Prevent MIME sniffing attacks
    - X-Frame-Options: Prevent clickjacking
    - CSP: Control resource loading to prevent injection attacks
    - Referrer-Policy: Limit referrer information leakage
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to response."""
        settings = get_cached_settings()
        
        response = await call_next(request)
        
        if settings.ENABLE_SECURITY_HEADERS:
            # HSTS: Force HTTPS
            # Include subdomains for subdomain protection
            # max-age in seconds (31536000 = 1 year)
            response.headers["Strict-Transport-Security"] = (
                f"max-age={settings.HSTS_MAX_AGE}; includeSubDomains; preload"
            )
            
            # Prevent MIME type sniffing
            # Stops browsers from trying to detect MIME type
            response.headers["X-Content-Type-Options"] = "nosniff"
            
            # Prevent clickjacking attacks
            # DENY: Page cannot be displayed in a frame
            # SAMEORIGIN: Page can only be displayed in a frame on the same origin
            response.headers["X-Frame-Options"] = "DENY"
            
            # XSS Protection (for older browsers)
            # 1; mode=block: Enable XSS filter and block page if attack detected
            response.headers["X-XSS-Protection"] = "1; mode=block"
            
            # Content Security Policy
            # Controls which resources can be loaded
            # This is a basic policy - customize based on your needs
            csp = (
                "default-src 'self'; "                          # Only allow from same origin
                "script-src 'self' 'unsafe-inline'; "            # Allow inline scripts if needed
                "style-src 'self' 'unsafe-inline'; "             # Allow inline styles if needed
                "img-src 'self' data: https:; "                  # Allow images from self, data URIs, https
                "font-src 'self' data:; "                        # Allow fonts from self and data URIs
                "connect-src 'self' https:; "                    # Allow API calls
                "frame-ancestors 'none'; "                       # Prevent framing
                "base-uri 'self'; "                              # Restrict base tag
                "form-action 'self'"                             # Restrict form submissions
            )
            response.headers["Content-Security-Policy"] = csp
            
            # Referrer Policy
            # Control how much referrer info is sent
            # strict-origin-when-cross-origin: Send origin for same-origin, nothing for cross-origin
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            
            # Permissions Policy (formerly Feature Policy)
            # Control browser features available to the page
            permissions = (
                "accelerometer=(), "
                "ambient-light-sensor=(), "
                "autoplay=(), "
                "camera=(), "
                "clipboard-read=(), "
                "clipboard-write=(), "
                "geolocation=(), "
                "gyroscope=(), "
                "magnetometer=(), "
                "microphone=(), "
                "payment=(), "
                "usb=()"
            )
            response.headers["Permissions-Policy"] = permissions
            
            # For API endpoints, disable caching
            if request.url.path.startswith("/api/"):
                response.headers["Cache-Control"] = (
                    "no-store, no-cache, must-revalidate, proxy-revalidate"
                )
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
            
            logger.debug(f"Security headers added for {request.url.path}")
        
        return response
