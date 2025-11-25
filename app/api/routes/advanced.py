"""
Advanced Patterns Routes Module

This module demonstrates advanced API patterns:
- WebSocket connections for real-time communication
- Server-Sent Events (SSE) for streaming
- Event-driven architecture
- Blocking vs async operations
- GraphQL integration (basic example)

These patterns are essential for modern, real-time applications.
"""

import asyncio
import json
from typing import AsyncGenerator, List
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from app.core.logging import get_logger
from app.utils.concurrency import run_in_thread_pool, run_in_process_pool, cpu_intensive_calculation
from app.db.memory import get_db

logger = get_logger(__name__)

# Create router for advanced patterns
advanced_router = APIRouter(tags=["Advanced Patterns"])


# ==================== WEBSOCKET ====================

class ConnectionManager:
    """
    WebSocket connection manager.
    
    Manages multiple WebSocket connections for broadcasting messages.
    Useful for chat applications, live updates, notifications, etc.
    """
    
    def __init__(self) -> None:
        # Active connections: {client_id: WebSocket}
        self.active_connections: dict[str, WebSocket] = {}
        logger.info("ConnectionManager initialized")
    
    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        """
        Accept and store a new WebSocket connection.
        
        Args:
            client_id: Unique client identifier
            websocket: WebSocket connection
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info("WebSocket connected", client_id=client_id, total=len(self.active_connections))
    
    def disconnect(self, client_id: str) -> None:
        """
        Remove a WebSocket connection.
        
        Args:
            client_id: Client identifier
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info("WebSocket disconnected", client_id=client_id, remaining=len(self.active_connections))
    
    async def send_personal_message(self, message: str, client_id: str) -> None:
        """
        Send message to specific client.
        
        Args:
            message: Message to send
            client_id: Target client ID
        """
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_text(message)
            logger.debug("Personal message sent", client_id=client_id)
    
    async def broadcast(self, message: str, exclude_client: str = None) -> None:
        """
        Broadcast message to all connected clients.
        
        Args:
            message: Message to broadcast
            exclude_client: Optional client ID to exclude from broadcast
        """
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            if client_id == exclude_client:
                continue
            
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error("Failed to send message", client_id=client_id, error=str(e))
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
        
        logger.debug("Message broadcasted", recipients=len(self.active_connections) - len(disconnected_clients))


# Global connection manager instance
manager = ConnectionManager()


@advanced_router.websocket("/ws/chat/{client_id}")
async def websocket_chat(websocket: WebSocket, client_id: str) -> None:
    """
    WebSocket endpoint for real-time chat.
    
    This demonstrates:
    - WebSocket connection handling
    - Real-time bidirectional communication
    - Broadcasting to multiple clients
    - Connection management
    
    Connect using JavaScript:
        const ws = new WebSocket('ws://localhost:8000/api/v1/ws/chat/user123');
        ws.onmessage = (event) => console.log(event.data);
        ws.send(JSON.stringify({type: 'message', content: 'Hello!'}));
    
    Args:
        websocket: WebSocket connection
        client_id: Unique client identifier from path
    """
    await manager.connect(client_id, websocket)
    
    # Send welcome message
    await manager.send_personal_message(
        json.dumps({
            "type": "system",
            "content": f"Welcome {client_id}! You are now connected.",
            "timestamp": datetime.utcnow().isoformat()
        }),
        client_id
    )
    
    # Notify others about new connection
    await manager.broadcast(
        json.dumps({
            "type": "system",
            "content": f"{client_id} joined the chat",
            "timestamp": datetime.utcnow().isoformat()
        }),
        exclude_client=client_id
    )
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                message_type = message_data.get("type", "message")
                content = message_data.get("content", "")
                
                logger.info("WebSocket message received", client_id=client_id, type=message_type)
                
                if message_type == "message":
                    # Broadcast message to all clients
                    broadcast_data = {
                        "type": "message",
                        "from": client_id,
                        "content": content,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await manager.broadcast(json.dumps(broadcast_data))
                
                elif message_type == "ping":
                    # Respond to ping with pong
                    await manager.send_personal_message(
                        json.dumps({"type": "pong", "timestamp": datetime.utcnow().isoformat()}),
                        client_id
                    )
                
            except json.JSONDecodeError:
                logger.warning("Invalid JSON received", client_id=client_id)
                await manager.send_personal_message(
                    json.dumps({"type": "error", "content": "Invalid message format"}),
                    client_id
                )
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        # Notify others about disconnection
        await manager.broadcast(
            json.dumps({
                "type": "system",
                "content": f"{client_id} left the chat",
                "timestamp": datetime.utcnow().isoformat()
            })
        )
    
    except Exception as e:
        logger.error("WebSocket error", client_id=client_id, error=str(e))
        manager.disconnect(client_id)


# ==================== SERVER-SENT EVENTS (SSE) ====================

async def generate_time_stream() -> AsyncGenerator[str, None]:
    """
    Generate time updates as Server-Sent Events.
    
    This is an async generator that yields events continuously.
    SSE is ideal for server-to-client streaming (one-way).
    """
    try:
        counter = 0
        while True:
            counter += 1
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "counter": counter,
                "message": f"Update #{counter}"
            }
            
            # Yield event data
            yield json.dumps(data)
            
            # Wait before next update
            await asyncio.sleep(1)
            
            # Stop after 60 updates (for demo purposes)
            if counter >= 60:
                logger.info("Time stream completed", updates=counter)
                break
    
    except asyncio.CancelledError:
        logger.info("Time stream cancelled by client")
        raise


@advanced_router.get("/stream/time")
async def stream_time(request: Request) -> EventSourceResponse:
    """
    Stream current time using Server-Sent Events (SSE).
    
    This demonstrates:
    - Server-Sent Events for one-way streaming
    - Real-time updates from server to client
    - Async generators
    
    Connect using JavaScript:
        const eventSource = new EventSource('http://localhost:8000/api/v1/stream/time');
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log(data.timestamp);
        };
    
    Returns:
        EventSourceResponse with time updates
    """
    logger.info("Time stream started", client=request.client.host if request.client else "unknown")
    return EventSourceResponse(generate_time_stream())


async def generate_data_stream(items: List[str]) -> AsyncGenerator[str, None]:
    """
    Generate data stream with processing updates.
    
    Simulates processing large datasets with progress updates.
    """
    total = len(items)
    
    for i, item in enumerate(items, 1):
        # Simulate processing time
        await asyncio.sleep(0.5)
        
        data = {
            "item": item,
            "progress": (i / total) * 100,
            "current": i,
            "total": total,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        yield json.dumps(data)
        
        logger.debug("Data stream progress", item=item, progress=f"{(i/total)*100:.1f}%")


@advanced_router.get("/stream/process")
async def stream_processing(request: Request) -> EventSourceResponse:
    """
    Stream data processing updates.
    
    Demonstrates streaming progress updates for long-running operations.
    Useful for showing progress bars, status updates, etc.
    
    Returns:
        EventSourceResponse with processing updates
    """
    # Sample data to process
    items = [f"item_{i}" for i in range(20)]
    
    logger.info("Processing stream started", items=len(items))
    return EventSourceResponse(generate_data_stream(items))


# ==================== BLOCKING VS ASYNC OPERATIONS ====================

@advanced_router.get("/demo/async-operation")
async def async_operation_demo() -> dict:
    """
    Demonstrate async (non-blocking) operation.
    
    This shows proper async/await usage for I/O-bound operations.
    Multiple async operations can run concurrently without blocking.
    
    Returns:
        Result of async operations with timing
    """
    import time
    start_time = time.time()
    
    # Simulate multiple async I/O operations running concurrently
    async def fetch_data(source: str, delay: float) -> dict:
        await asyncio.sleep(delay)  # Simulates I/O wait
        return {"source": source, "data": f"Data from {source}"}
    
    # Run multiple operations concurrently
    results = await asyncio.gather(
        fetch_data("database", 1.0),
        fetch_data("cache", 0.5),
        fetch_data("api", 1.5)
    )
    
    duration = time.time() - start_time
    
    logger.info("Async operations completed", duration_seconds=round(duration, 2))
    
    return {
        "type": "async",
        "operations": results,
        "duration_seconds": round(duration, 2),
        "note": "Operations ran concurrently (not sequentially)"
    }


@advanced_router.get("/demo/blocking-operation")
async def blocking_operation_demo() -> dict:
    """
    Demonstrate blocking operation in thread pool.
    
    This shows how to integrate blocking/synchronous code with async FastAPI.
    Blocking code runs in a thread pool to avoid blocking the event loop.
    
    Returns:
        Result of blocking operations with timing
    """
    import time
    start_time = time.time()
    
    # Blocking function that simulates CPU-bound work
    def blocking_task(name: str, duration: float) -> dict:
        time.sleep(duration)  # This would block if not in thread pool
        return {"task": name, "result": f"Completed {name}"}
    
    # Run blocking operations in thread pool
    result = await run_in_thread_pool(blocking_task, "data_processing", 2.0)
    
    duration = time.time() - start_time
    
    logger.info("Blocking operation completed", duration_seconds=round(duration, 2))
    
    return {
        "type": "blocking_in_thread_pool",
        "operation": result,
        "duration_seconds": round(duration, 2),
        "note": "Blocking operation ran in thread pool without blocking event loop"
    }


@advanced_router.get("/demo/cpu-intensive")
async def cpu_intensive_demo(n: int = 30) -> dict:
    """
    Demonstrate CPU-intensive operation in process pool.
    
    This shows how to handle CPU-bound operations that benefit from
    parallel processing across multiple CPU cores.
    
    Args:
        n: Input for CPU-intensive calculation (default 30, max 35)
        
    Returns:
        Result of CPU-intensive calculation with timing
    """
    import time
    start_time = time.time()
    
    # Cap input to prevent excessive computation
    n = min(n, 35)
    
    # Run CPU-intensive task in process pool
    result = await run_in_process_pool(cpu_intensive_calculation, n)
    
    duration = time.time() - start_time
    
    logger.info("CPU-intensive operation completed", input=n, duration_seconds=round(duration, 2))
    
    return {
        "type": "cpu_intensive_in_process_pool",
        "input": n,
        "result": result,
        "duration_seconds": round(duration, 2),
        "note": "CPU-intensive operation ran in separate process"
    }


# ==================== EVENT-DRIVEN PATTERN ====================

class EventBus:
    """
    Simple event bus for event-driven architecture.
    
    Implements publish-subscribe pattern for loose coupling between components.
    """
    
    def __init__(self) -> None:
        self.subscribers: dict[str, list] = {}
        logger.info("EventBus initialized")
    
    def subscribe(self, event_type: str, handler: callable) -> None:
        """Subscribe to an event type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
        logger.debug("Event handler subscribed", event_type=event_type)
    
    async def publish(self, event_type: str, data: dict) -> None:
        """Publish an event to all subscribers."""
        if event_type in self.subscribers:
            logger.info("Event published", event_type=event_type, subscribers=len(self.subscribers[event_type]))
            
            for handler in self.subscribers[event_type]:
                try:
                    await handler(data)
                except Exception as e:
                    logger.error("Event handler failed", event_type=event_type, error=str(e))


# Global event bus
event_bus = EventBus()


# Example event handlers
async def log_user_created(data: dict) -> None:
    """Log when user is created."""
    logger.info("Event: User created", user_id=data.get("user_id"))


async def send_welcome_email(data: dict) -> None:
    """Simulate sending welcome email."""
    await asyncio.sleep(0.5)  # Simulate email sending
    logger.info("Event: Welcome email sent", user_id=data.get("user_id"))


# Subscribe handlers to events
event_bus.subscribe("user.created", log_user_created)
event_bus.subscribe("user.created", send_welcome_email)


@advanced_router.post("/demo/event")
async def trigger_event(event_type: str, data: dict) -> dict:
    """
    Trigger an event in the event bus.
    
    This demonstrates event-driven architecture where actions trigger
    events that other components can react to asynchronously.
    
    Args:
        event_type: Type of event to trigger
        data: Event data
        
    Returns:
        Event confirmation
    """
    await event_bus.publish(event_type, data)
    
    return {
        "message": "Event published",
        "event_type": event_type,
        "subscribers_notified": len(event_bus.subscribers.get(event_type, [])),
        "timestamp": datetime.utcnow().isoformat()
    }


# ==================== STREAMING RESPONSE ====================

async def generate_large_data() -> AsyncGenerator[bytes, None]:
    """
    Generate large dataset in chunks.
    
    This demonstrates streaming large responses to avoid memory issues.
    """
    # Simulate generating large CSV file
    yield b"id,name,value,timestamp\n"
    
    for i in range(1000):
        row = f"{i},item_{i},{i * 10},{datetime.utcnow().isoformat()}\n"
        yield row.encode()
        
        # Yield control to event loop
        if i % 100 == 0:
            await asyncio.sleep(0.01)


@advanced_router.get("/stream/large-data")
async def stream_large_data() -> StreamingResponse:
    """
    Stream large dataset as CSV.
    
    This demonstrates:
    - Streaming large responses
    - Memory-efficient data transfer
    - Chunked transfer encoding
    
    Returns:
        StreamingResponse with CSV data
    """
    logger.info("Large data streaming started")
    
    return StreamingResponse(
        generate_large_data(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=data.csv"}
    )
