"""
Integration Tests for Health and Monitoring Endpoints

Tests health checks, metrics, readiness, and liveness probes.
"""

import pytest
from fastapi import status


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_health_check(async_client):
    """Test basic health check endpoint."""
    response = await async_client.get("/api/v1/health")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_detailed_health_check(async_client):
    """Test detailed health check with component status."""
    response = await async_client.get("/api/v1/health/detailed")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert "status" in data
    assert "components" in data
    assert "database" in data["components"]
    assert "cache" in data["components"]
    
    # Verify component health
    assert data["components"]["database"]["status"] in ["healthy", "unhealthy"]
    assert data["components"]["cache"]["status"] in ["healthy", "unhealthy"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metrics_endpoint(async_client):
    """Test metrics endpoint returns application metrics."""
    response = await async_client.get("/api/v1/metrics")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Basic metrics
    assert "uptime" in data
    assert "requests_total" in data
    assert "database" in data
    assert "cache" in data
    
    # Database metrics
    db_metrics = data["database"]
    assert "total_items" in db_metrics
    assert "collections" in db_metrics
    
    # Cache metrics
    cache_metrics = data["cache"]
    assert "size" in cache_metrics
    assert "hits" in cache_metrics
    assert "misses" in cache_metrics


@pytest.mark.integration
@pytest.mark.asyncio
async def test_readiness_probe(async_client):
    """Test Kubernetes readiness probe."""
    response = await async_client.get("/api/v1/ready")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["ready"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_liveness_probe(async_client):
    """Test Kubernetes liveness probe."""
    response = await async_client.get("/api/v1/live")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["alive"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_after_operations(async_client, sample_user_data):
    """Test health check reflects system state after operations."""
    # Perform some operations
    await async_client.post("/api/v1/users", json=sample_user_data)
    await async_client.get("/api/v1/users")
    
    # Check health
    response = await async_client.get("/api/v1/health/detailed")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Database should show activity
    db_status = data["components"]["database"]
    assert "item_count" in db_status or "collections" in db_status


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metrics_increment(async_client, sample_user_data):
    """Test metrics increment with requests."""
    # Get initial metrics
    response1 = await async_client.get("/api/v1/metrics")
    initial_requests = response1.json()["requests_total"]
    
    # Make some requests
    await async_client.post("/api/v1/users", json=sample_user_data)
    await async_client.get("/api/v1/users")
    
    # Get updated metrics
    response2 = await async_client.get("/api/v1/metrics")
    final_requests = response2.json()["requests_total"]
    
    # Requests should have increased
    assert final_requests > initial_requests


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_hit_rate_in_metrics(async_client, create_test_user, cache):
    """Test cache metrics show hit rate."""
    # Create user and get it multiple times (to generate cache hits)
    user = await create_test_user(name="Cache Test User")
    
    # First request (cache miss)
    await async_client.get(f"/api/v1/users/{user['id']}")
    
    # Second request (cache hit)
    await async_client.get(f"/api/v1/users/{user['id']}")
    
    # Check metrics
    response = await async_client.get("/api/v1/metrics")
    cache_metrics = response.json()["cache"]
    
    assert cache_metrics["hits"] > 0 or cache_metrics["misses"] > 0
    
    # Calculate hit rate if both hits and misses exist
    if cache_metrics["hits"] > 0 and cache_metrics["misses"] > 0:
        hit_rate = cache_metrics["hits"] / (cache_metrics["hits"] + cache_metrics["misses"])
        assert 0 <= hit_rate <= 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_connection_health(async_client, db):
    """Test database health check detects connection."""
    response = await async_client.get("/api/v1/health/detailed")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Database should be healthy
    assert data["components"]["database"]["status"] == "healthy"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_system_metrics(async_client):
    """Test system-level metrics are included."""
    response = await async_client.get("/api/v1/metrics")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Should include system metrics
    assert "uptime" in data
    assert isinstance(data["uptime"], (int, float))
    assert data["uptime"] >= 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_check_response_time(async_client, benchmark_timer):
    """Test health check responds quickly."""
    async with benchmark_timer("health_check") as timer:
        response = await async_client.get("/api/v1/health")
    
    assert response.status_code == status.HTTP_200_OK
    # Health checks should be fast (< 100ms)
    assert timer.elapsed < 0.1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metrics_endpoint_response_time(async_client, benchmark_timer):
    """Test metrics endpoint responds quickly."""
    async with benchmark_timer("metrics") as timer:
        response = await async_client.get("/api/v1/metrics")
    
    assert response.status_code == status.HTTP_200_OK
    # Metrics should be fast (< 200ms)
    assert timer.elapsed < 0.2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_check_format(async_client):
    """Test health check response format."""
    response = await async_client.get("/api/v1/health")
    
    data = response.json()
    
    # Verify required fields
    assert isinstance(data["status"], str)
    assert data["status"] in ["healthy", "unhealthy", "degraded"]
    assert isinstance(data["timestamp"], str)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_detailed_health_check_format(async_client):
    """Test detailed health check response format."""
    response = await async_client.get("/api/v1/health/detailed")
    
    data = response.json()
    
    # Verify structure
    assert isinstance(data["components"], dict)
    
    # Each component should have required fields
    for component_name, component_data in data["components"].items():
        assert "status" in component_data
        assert component_data["status"] in ["healthy", "unhealthy", "degraded"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_health_checks(async_client):
    """Test health check handles concurrent requests."""
    import asyncio
    
    # Make multiple concurrent health check requests
    tasks = [
        async_client.get("/api/v1/health")
        for _ in range(20)
    ]
    
    responses = await asyncio.gather(*tasks)
    
    # All should succeed
    assert all(r.status_code == status.HTTP_200_OK for r in responses)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_check_during_load(async_client, create_test_user):
    """Test health check remains responsive during load."""
    import asyncio
    
    # Create background load
    load_tasks = [
        create_test_user(name=f"User {i}", email=f"user{i}@example.com")
        for i in range(10)
    ]
    
    # Make health check during load
    health_task = async_client.get("/api/v1/health")
    
    # Run concurrently
    results = await asyncio.gather(*load_tasks, health_task)
    
    # Health check should still succeed
    health_response = results[-1]
    assert health_response.status_code == status.HTTP_200_OK
