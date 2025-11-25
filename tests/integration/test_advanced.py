"""
Integration Tests for Advanced API Features

Tests WebSocket, SSE, streaming, and event-driven patterns.
"""

import pytest
import asyncio
import json
from fastapi import status


# ==================== WEBSOCKET TESTS ====================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_websocket_connection(async_client):
    """Test establishing WebSocket connection."""
    async with async_client.websocket_connect("/api/v1/ws/chat") as websocket:
        # Receive connection message
        data = await websocket.receive_json()
        assert "type" in data
        assert data["type"] == "connection"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_websocket_echo(async_client):
    """Test WebSocket echo functionality."""
    async with async_client.websocket_connect("/api/v1/ws/chat") as websocket:
        # Skip connection message
        await websocket.receive_json()
        
        # Send message
        test_message = {"type": "message", "content": "Hello WebSocket!"}
        await websocket.send_json(test_message)
        
        # Receive echo
        response = await websocket.receive_json()
        assert response["content"] == "Hello WebSocket!"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_websocket_broadcast(async_client):
    """Test WebSocket broadcast to multiple clients."""
    # Connect two clients
    async with async_client.websocket_connect("/api/v1/ws/chat") as ws1, \
               async_client.websocket_connect("/api/v1/ws/chat") as ws2:
        
        # Skip connection messages
        await ws1.receive_json()
        await ws2.receive_json()
        
        # Send from client 1
        await ws1.send_json({"type": "message", "content": "Broadcast test"})
        
        # Both clients should receive the message
        msg1 = await ws1.receive_json()
        msg2 = await ws2.receive_json()
        
        assert msg1["content"] == "Broadcast test"
        assert msg2["content"] == "Broadcast test"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_websocket_disconnect(async_client):
    """Test WebSocket disconnect handling."""
    async with async_client.websocket_connect("/api/v1/ws/chat") as websocket:
        await websocket.receive_json()  # Connection message
        
        # Send disconnect
        await websocket.send_json({"type": "disconnect"})
        
        # Connection should close
        with pytest.raises(Exception):  # WebSocket closes
            await websocket.receive_json()


# ==================== SERVER-SENT EVENTS (SSE) TESTS ====================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_sse_stream(async_client):
    """Test Server-Sent Events streaming."""
    response = await async_client.get("/api/v1/sse/stream")
    
    assert response.status_code == status.HTTP_200_OK
    assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sse_time_updates(async_client):
    """Test SSE sends periodic time updates."""
    # Note: This is a simplified test. In real scenarios, you'd need
    # to stream the response and verify multiple events
    response = await async_client.get("/api/v1/sse/stream")
    
    assert response.status_code == status.HTTP_200_OK


# ==================== ASYNC VS BLOCKING TESTS ====================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_async_operation_non_blocking(async_client):
    """Test async operations are non-blocking."""
    import time
    
    start = time.time()
    
    # Make multiple concurrent async requests
    tasks = [
        async_client.get("/api/v1/async-demo")
        for _ in range(5)
    ]
    responses = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    
    # All should succeed
    assert all(r.status_code == status.HTTP_200_OK for r in responses)
    
    # Should complete quickly due to concurrency
    print(f"\nAsync operations took: {elapsed:.3f}s")
    assert elapsed < 3.0  # Should be much faster than 5 * 1s


@pytest.mark.integration
@pytest.mark.asyncio
async def test_blocking_operation(async_client):
    """Test blocking operation runs in thread pool."""
    response = await async_client.get("/api/v1/blocking-demo")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "result" in data
    assert "duration" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cpu_intensive_operation(async_client):
    """Test CPU-intensive operation runs in process pool."""
    response = await async_client.post(
        "/api/v1/cpu-intensive",
        json={"iterations": 100000}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "result" in data
    assert "duration" in data
    assert isinstance(data["result"], float)


# ==================== EVENT-DRIVEN TESTS ====================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_event_publish_and_subscribe(async_client):
    """Test event publishing and subscription."""
    # Subscribe to events
    response = await async_client.post(
        "/api/v1/events/subscribe",
        json={"event_type": "user.created"}
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Publish event
    response = await async_client.post(
        "/api/v1/events/publish",
        json={
            "event_type": "user.created",
            "data": {"user_id": 1, "username": "testuser"}
        }
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_event_subscribers(async_client):
    """Test multiple subscribers receive events."""
    event_type = "test.event"
    
    # Subscribe multiple handlers
    for i in range(3):
        await async_client.post(
            "/api/v1/events/subscribe",
            json={"event_type": event_type}
        )
    
    # Publish event
    response = await async_client.post(
        "/api/v1/events/publish",
        json={
            "event_type": event_type,
            "data": {"message": "Test event"}
        }
    )
    
    assert response.status_code == status.HTTP_200_OK


# ==================== STREAMING TESTS ====================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_stream_large_data(async_client):
    """Test streaming large dataset."""
    response = await async_client.get("/api/v1/stream/data?size=1000")
    
    assert response.status_code == status.HTTP_200_OK
    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_stream_file_download(async_client):
    """Test streaming file download."""
    response = await async_client.get("/api/v1/stream/download")
    
    assert response.status_code == status.HTTP_200_OK
    # Verify streaming headers
    assert "chunked" in response.headers.get("transfer-encoding", "").lower() or \
           "content-length" in response.headers


# ==================== CONCURRENT OPERATIONS TESTS ====================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_user_creation(async_client, sample_users_data):
    """Test creating multiple users concurrently."""
    # Create tasks for concurrent user creation
    tasks = [
        async_client.post("/api/v1/users", json=user_data)
        for user_data in sample_users_data[:5]  # First 5 users
    ]
    
    responses = await asyncio.gather(*tasks)
    
    # All should succeed
    assert all(r.status_code == status.HTTP_201_CREATED for r in responses)
    
    # All should have unique IDs
    ids = [r.json()["id"] for r in responses]
    assert len(set(ids)) == len(ids)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_reads(async_client, create_test_user):
    """Test concurrent read operations."""
    # Create a user
    user = await create_test_user(name="Concurrent Test User")
    
    # Perform concurrent reads
    tasks = [
        async_client.get(f"/api/v1/users/{user['id']}")
        for _ in range(50)
    ]
    
    responses = await asyncio.gather(*tasks)
    
    # All should succeed
    assert all(r.status_code == status.HTTP_200_OK for r in responses)
    
    # All should return same data
    assert all(r.json()["id"] == user["id"] for r in responses)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mixed_concurrent_operations(async_client, sample_user_data):
    """Test mixed read/write operations concurrently."""
    # Create initial user
    create_response = await async_client.post("/api/v1/users", json=sample_user_data)
    user_id = create_response.json()["id"]
    
    # Mix of operations
    tasks = [
        async_client.get(f"/api/v1/users/{user_id}"),  # Read
        async_client.patch(f"/api/v1/users/{user_id}", json={"age": 31}),  # Update
        async_client.get(f"/api/v1/users/{user_id}"),  # Read
        async_client.get("/api/v1/users"),  # List
    ]
    
    responses = await asyncio.gather(*tasks)
    
    # All should succeed or return expected status
    assert all(r.status_code in [200, 304] for r in responses)


# ==================== LONG-POLLING TESTS ====================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_long_polling_timeout(async_client):
    """Test long-polling request timeout handling."""
    # Make long-polling request with short timeout
    response = await async_client.get(
        "/api/v1/poll/updates?timeout=1",
        timeout=2.0
    )
    
    # Should return even if no updates (timeout)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]


# ==================== BATCH OPERATIONS TESTS ====================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_user_creation(async_client, sample_users_data):
    """Test batch creation of users."""
    response = await async_client.post(
        "/api/v1/users/batch",
        json={"users": sample_users_data}
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "created" in data
    assert len(data["created"]) == len(sample_users_data)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_operations_partial_failure(async_client, sample_user_data):
    """Test batch operations handle partial failures."""
    # Create valid and invalid users
    users = [
        sample_user_data,
        {**sample_user_data, "email": "invalid-email"},  # Invalid
    ]
    
    response = await async_client.post(
        "/api/v1/users/batch",
        json={"users": users}
    )
    
    # Should return partial success info
    data = response.json()
    assert "created" in data or "errors" in data


# ==================== DATA PROCESSING TESTS ====================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_numerical_analysis_endpoint(async_client):
    """Test numerical data analysis endpoint."""
    data = {
        "values": [1.5, 2.7, 3.2, 4.8, 5.1, 6.3, 7.9, 8.2, 9.5, 10.1]
    }
    
    response = await async_client.post("/api/v1/analyze/numerical", json=data)
    
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert "mean" in result
    assert "median" in result
    assert "std_dev" in result


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dataframe_processing_endpoint(async_client):
    """Test DataFrame processing endpoint."""
    data = {
        "data": [
            {"name": "Alice", "age": 30, "score": 85.5},
            {"name": "Bob", "age": 25, "score": 92.3},
            {"name": "Charlie", "age": 35, "score": 78.9}
        ]
    }
    
    response = await async_client.post("/api/v1/analyze/dataframe", json=data)
    
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert "statistics" in result


# ==================== ERROR HANDLING IN CONCURRENT OPERATIONS ====================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_operations_with_errors(async_client):
    """Test error handling in concurrent operations."""
    # Mix of valid and invalid requests
    tasks = [
        async_client.get("/api/v1/users/1"),  # Might not exist
        async_client.get("/api/v1/users/999"),  # Definitely doesn't exist
        async_client.get("/api/v1/users"),  # Valid
    ]
    
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Should handle both successes and failures
    assert len(responses) == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_timeout_handling_in_streaming(async_client):
    """Test timeout handling in streaming responses."""
    # Request with timeout parameter
    response = await async_client.get(
        "/api/v1/stream/data?size=1000000&timeout=1"
    )
    
    # Should handle gracefully
    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_408_REQUEST_TIMEOUT,
        status.HTTP_504_GATEWAY_TIMEOUT
    ]
