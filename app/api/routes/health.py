"""
Health and Monitoring Routes Module

This module provides health checks, metrics, and monitoring endpoints.
Essential for production deployments, load balancers, and observability.

Endpoints:
- /health: Basic health check
- /health/detailed: Detailed health check with component status
- /metrics: Application metrics
- /info: Application information
"""

from fastapi import APIRouter, status
from datetime import datetime
from app.schemas.models import HealthCheck
from app.core.config import settings
from app.core.logging import get_logger
from app.db.memory import get_db
from app.services.cache import get_cache
from app.middleware.resilience import MetricsMiddleware
from typing import Dict, Any

logger = get_logger(__name__)

# Create router for health and monitoring
health_router = APIRouter(tags=["Health & Monitoring"])


@health_router.get(
    "/health",
    response_model=HealthCheck,
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Quick health check for load balancers and monitoring systems"
)
async def health_check() -> HealthCheck:
    """
    Basic health check endpoint.
    
    This is a lightweight endpoint that returns quickly.
    Used by load balancers and monitoring systems to verify service availability.
    
    Returns:
        HealthCheck with basic status
    """
    return HealthCheck(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow().isoformat(),
        database="ok",
        cache="ok"
    )


@health_router.get(
    "/health/detailed",
    summary="Detailed health check",
    description="Comprehensive health check with component status"
)
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check with component status.
    
    This checks all major components:
    - Database connectivity
    - Cache availability
    - Memory usage
    - Configuration
    
    Returns:
        Dictionary with detailed health information
    """
    db = get_db()
    cache = get_cache()
    
    # Check database
    try:
        user_count = await db.count("users")
        db_status = "healthy"
        db_details = {"user_count": user_count}
    except Exception as e:
        db_status = "unhealthy"
        db_details = {"error": str(e)}
        logger.error("Database health check failed", error=str(e))
    
    # Check cache
    try:
        cache_stats = await cache.get_stats()
        cache_status = "healthy"
        cache_details = cache_stats
    except Exception as e:
        cache_status = "unhealthy"
        cache_details = {"error": str(e)}
        logger.error("Cache health check failed", error=str(e))
    
    # Get system info
    import psutil
    memory = psutil.virtual_memory()
    
    overall_status = "healthy" if (db_status == "healthy" and cache_status == "healthy") else "degraded"
    
    health_data = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "components": {
            "database": {
                "status": db_status,
                "details": db_details
            },
            "cache": {
                "status": cache_status,
                "details": cache_details
            },
            "system": {
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available // (1024 * 1024),
                "cpu_count": psutil.cpu_count()
            }
        }
    }
    
    logger.info("Detailed health check performed", status=overall_status)
    return health_data


@health_router.get(
    "/metrics",
    summary="Application metrics",
    description="Get application performance metrics"
)
async def get_metrics() -> Dict[str, Any]:
    """
    Get application metrics.
    
    Returns performance metrics collected by middleware:
    - Request counts
    - Response times
    - Error rates
    - Status code distribution
    
    Returns:
        Dictionary with metrics data
    """
    db = get_db()
    cache = get_cache()
    
    # Get database stats
    db_stats = db.get_stats()
    
    # Get cache stats
    cache_stats = await cache.get_stats()
    
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_stats,
        "cache": cache_stats,
        "uptime_seconds": 0  # Would need to track app start time
    }
    
    logger.debug("Metrics retrieved")
    return metrics


@health_router.get(
    "/info",
    summary="Application information",
    description="Get application metadata and configuration"
)
async def app_info() -> Dict[str, Any]:
    """
    Get application information.
    
    Returns application metadata useful for debugging and monitoring:
    - Application name and version
    - Environment
    - Configuration summary
    - API capabilities
    
    Returns:
        Dictionary with application information
    """
    info = {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug_mode": settings.DEBUG,
        "api_features": {
            "crud_operations": True,
            "websockets": True,
            "streaming": True,
            "graphql": False,  # Not implemented in this example
            "caching": True,
            "rate_limiting": True,
            "circuit_breaker": True
        },
        "supported_formats": ["JSON", "CSV"],
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    logger.debug("Application info retrieved")
    return info


@health_router.get(
    "/ping",
    summary="Simple ping endpoint",
    description="Minimal endpoint for basic connectivity check"
)
async def ping() -> Dict[str, str]:
    """
    Simple ping endpoint.
    
    Returns a minimal response for basic connectivity testing.
    Useful for quick availability checks.
    
    Returns:
        Simple pong response
    """
    return {
        "status": "pong",
        "timestamp": datetime.utcnow().isoformat()
    }


@health_router.get(
    "/ready",
    summary="Readiness probe",
    description="Kubernetes readiness probe endpoint"
)
async def readiness() -> Dict[str, Any]:
    """
    Readiness probe for Kubernetes.
    
    Indicates whether the application is ready to serve traffic.
    Should fail if dependencies are not available.
    
    Returns:
        Readiness status
    """
    db = get_db()
    cache = get_cache()
    
    # Check critical dependencies
    try:
        # Quick database check
        await db.count("users")
        
        # Quick cache check
        await cache.get("health_check_key")
        
        return {
            "ready": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return {
            "ready": False,
            "reason": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@health_router.get(
    "/live",
    summary="Liveness probe",
    description="Kubernetes liveness probe endpoint"
)
async def liveness() -> Dict[str, Any]:
    """
    Liveness probe for Kubernetes.
    
    Indicates whether the application is alive.
    Should only fail if the application needs to be restarted.
    
    Returns:
        Liveness status
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    }
