"""
FastAPI Comprehensive Guide - Main Application

This is the main entry point for the FastAPI application.
It demonstrates best practices for application structure, middleware configuration,
error handling, and API documentation.

Key Features:
- RESTful API with all HTTP verbs
- WebSocket support
- Server-Sent Events
- Caching
- Rate limiting (endpoint-specific)
- Circuit breaker pattern
- Security: JWT, OAuth2, RBAC
- Token refresh and blacklist
- File upload with validation
- Advanced parameter validation
- Comprehensive error handling
- Health checks and monitoring
- OpenAPI/Swagger documentation
- Security headers (HSTS, CSP, etc.)
- OpenTelemetry observability

To run the application:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    
Or using the run script:
    python -m app.main
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from datetime import datetime
from typing import AsyncGenerator

from app.core.config import get_cached_settings
from app.core.logging import get_logger, RequestLogMiddleware
from app.middleware.resilience import RateLimitMiddleware, TimeoutMiddleware, MetricsMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.services.cache import init_cache, shutdown_cache
from app.utils.concurrency import shutdown_executors
from app.api.routes.crud import crud_router
from app.api.routes.advanced import advanced_router
from app.api.routes.health import health_router
from app.api.routes.advanced_security import security_router
from app.api.routes.file_uploads import files_router
from app.api.routes.advanced_parameters import advanced_params_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events:
    - Startup: Initialize caches, connections, background tasks
    - Shutdown: Cleanup resources, close connections
    
    This is the modern way to handle startup/shutdown (FastAPI 0.93+)
    replacing @app.on_event("startup") and @app.on_event("shutdown")
    """
    # Startup
    settings = get_cached_settings()
    logger.info(
        "Application starting",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG
    )
    
    # Initialize cache
    await init_cache()
    logger.info("Cache initialization complete")
    
    # Initialize database with sample data if in development
    if settings.is_development():
        from app.db.memory import get_db
        db = get_db()
        
        # Add sample users
        sample_users = [
            {"name": "Alice Smith", "email": "alice@example.com", "age": 30, "role": "admin", "is_active": True},
            {"name": "Bob Johnson", "email": "bob@example.com", "age": 25, "role": "user", "is_active": True},
            {"name": "Charlie Brown", "email": "charlie@example.com", "age": 35, "role": "user", "is_active": False},
        ]
        
        for user_data in sample_users:
            await db.create("users", user_data)
        
        # Add sample products
        sample_products = [
            {"name": "Laptop", "description": "High-performance laptop", "price": 999.99, "stock": 50, "category": "Electronics", "tags": ["computer", "portable"]},
            {"name": "Mouse", "description": "Wireless mouse", "price": 29.99, "stock": 200, "category": "Electronics", "tags": ["accessory", "wireless"]},
            {"name": "Desk", "description": "Standing desk", "price": 399.99, "stock": 15, "category": "Furniture", "tags": ["office", "adjustable"]},
        ]
        
        for product_data in sample_products:
            await db.create("products", product_data)
        
        logger.info("Sample data loaded", users=len(sample_users), products=len(sample_products))
    
    logger.info("Application startup complete")
    
    yield  # Application is running
    
    # Shutdown
    logger.info("Application shutting down")
    
    # Shutdown cache
    await shutdown_cache()
    logger.info("Cache shutdown complete")
    
    # Shutdown thread/process pools
    await shutdown_executors()
    logger.info("Executors shutdown complete")
    
    logger.info("Application shutdown complete")


# Create FastAPI application
settings = get_cached_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="""
    # FastAPI Comprehensive Guide
    
    A comprehensive guide and example project for building production-ready APIs with FastAPI.
    
    ## Features
    
    * **RESTful API**: Full CRUD operations with all HTTP verbs
    * **Authentication**: JWT tokens, refresh tokens, token blacklist
    * **Authorization**: Role-based access control (RBAC)
    * **Advanced Patterns**: WebSocket, SSE, GraphQL integration
    * **File Uploads**: Validated uploads with streaming support
    * **Caching**: In-memory and Redis caching with ETag support
    * **Resilience**: Circuit breaker, rate limiting, timeouts
    * **Security**: HSTS, CSP, CORS, RS256/HS256 JWT
    * **Observability**: Health checks, metrics, structured logging, OpenTelemetry
    * **Performance**: Async/await, thread pools, process pools
    * **Best Practices**: Type hints, validation, error handling
    
    ## Getting Started
    
    1. Explore the interactive API documentation below
    2. Try the `/health` endpoint for a quick check
    3. Register user: POST `/api/v1/security/register`
    4. Login: POST `/api/v1/security/token`
    5. Use token in Authorization header: `Bearer <token>`
    
    ## Authentication
    
    - Login endpoint: POST `/api/v1/security/token`
    - Register endpoint: POST `/api/v1/security/register`
    - Refresh token: POST `/api/v1/security/refresh`
    - Logout: POST `/api/v1/security/logout`
    
    ## Rate Limiting
    
    - General endpoints: 100 requests per 60 seconds
    - Auth endpoints: 5 requests per 300 seconds
    - Upload endpoints: 10 requests per 300 seconds
    """,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    debug=settings.DEBUG,
)


# ==================== MIDDLEWARE CONFIGURATION ====================

# Security Headers Middleware (HSTS, CSP, X-Frame-Options, etc.)
# Add this FIRST to ensure headers are applied to all responses
app.add_middleware(SecurityHeadersMiddleware)

# Request Logging Middleware
# Logs all incoming requests with structured data
app.add_middleware(RequestLogMiddleware)

# Rate Limiting Middleware
# Endpoint-specific rate limits: auth, upload, general
app.add_middleware(RateLimitMiddleware)

# Timeout Middleware
# Prevents slow requests from consuming resources
app.add_middleware(TimeoutMiddleware, timeout=settings.REQUEST_TIMEOUT)

# Metrics Middleware
# Tracks response times and status codes
app.add_middleware(MetricsMiddleware)

# GZip Compression Middleware
# Compress responses larger than 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS Middleware (Cross-Origin Resource Sharing)
# Allows frontend applications to call API
# Production: Restrict to specific origins
cors_origins = settings.CORS_ORIGINS
if settings.is_production():
    # Production: Very restrictive
    logger.warning(f"Production CORS origins: {cors_origins}")
else:
    logger.info(f"Development CORS origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# GZip compression middleware - compresses responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Custom middleware
app.add_middleware(RequestLogMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(TimeoutMiddleware, timeout=settings.REQUEST_TIMEOUT)
app.add_middleware(RateLimitMiddleware)


# ==================== EXCEPTION HANDLERS ====================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle 404 Not Found errors."""
    logger.warning("Not found", path=request.url.path, method=request.method)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "not_found",
            "message": "The requested resource was not found",
            "path": request.url.path,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle 500 Internal Server Error."""
    logger.error(
        "Internal server error",
        path=request.url.path,
        method=request.method,
        error=str(exc)
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An internal server error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    
    # Don't expose internal errors in production
    if settings.is_production:
        message = "An error occurred processing your request"
    else:
        message = str(exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "server_error",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# ==================== ROUTERS ====================

# Include API routers with prefix
app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(crud_router, prefix="/api/v1", tags=["CRUD"])
app.include_router(advanced_router, prefix="/api/v1", tags=["Advanced"])
app.include_router(security_router, prefix="/api/v1", tags=["Security & OAuth2"])
app.include_router(files_router, prefix="/api/v1", tags=["File Upload"])
app.include_router(advanced_params_router, prefix="/api/v1", tags=["Advanced Parameters"])


# ==================== ROOT ENDPOINTS ====================

@app.get(
    "/",
    summary="API Root",
    description="Get API information and available endpoints",
    tags=["Root"]
)
async def root() -> dict:
    """
    API root endpoint.
    
    Returns basic information about the API and links to documentation.
    """
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_spec": "/openapi.json"
        },
        "endpoints": {
            "health": "/api/v1/health",
            "metrics": "/api/v1/metrics",
            "users": "/api/v1/users",
            "products": "/api/v1/products",
            "websocket_chat": "/api/v1/ws/chat/{client_id}",
            "stream": "/api/v1/stream/time"
        },
        "message": "Welcome to FastAPI Comprehensive Guide! Visit /docs for interactive API documentation.",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Return empty response for favicon requests."""
    return JSONResponse(content={}, status_code=204)


# ==================== CUSTOM OPENAPI SCHEMA ====================

def custom_openapi():
    """
    Customize OpenAPI schema.
    
    This adds additional metadata and customizations to the API documentation.
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=app.description,
        routes=app.routes,
    )
    
    # Add additional info
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    
    # Add tags metadata
    openapi_schema["tags"] = [
        {
            "name": "Health",
            "description": "Health checks and monitoring endpoints"
        },
        {
            "name": "CRUD",
            "description": "CRUD operations for users and products"
        },
        {
            "name": "Advanced",
            "description": "Advanced patterns: WebSocket, SSE, streaming, events"
        },
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ==================== DEVELOPMENT SERVER ====================

if __name__ == "__main__":
    """
    Run the application directly for development.
    
    For production, use a production ASGI server like Gunicorn with Uvicorn workers:
        gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
    """
    import uvicorn
    
    logger.info(
        "Starting development server",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD
    )
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )
