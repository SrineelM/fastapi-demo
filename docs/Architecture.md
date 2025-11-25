# FastAPI Architecture Guide

## System Architecture Overview

This document describes the architecture, design patterns, and technical decisions behind the FastAPI Comprehensive Guide project.

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Component Architecture](#component-architecture)
3. [Design Patterns](#design-patterns)
4. [Data Flow](#data-flow)
5. [Concurrency Model](#concurrency-model)
6. [Security Architecture](#security-architecture)
7. [Scalability Architecture](#scalability-architecture)
8. [Observability Architecture](#observability-architecture)

---

## High-Level Architecture

### Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                             │
│  (Web Browsers, Mobile Apps, CLI Tools, Other Services)     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ HTTP/WebSocket/SSE
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   API Gateway Layer                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Rate Limit  │  │   Circuit    │  │   Timeout    │       │
│  │ Middleware  │  │   Breaker    │  │  Middleware  │       │
│  └─────────────┘  └──────────────┘  └──────────────┘       │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    Routing Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ CRUD Routes  │  │  Advanced    │  │   Health     │      │
│  │              │  │   Routes     │  │   Routes     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   Business Logic Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Service    │  │    Cache     │  │    Event     │      │
│  │   Layer      │  │   Service    │  │     Bus      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    Data Access Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  In-Memory   │  │    Cache     │  │   External   │      │
│  │  Database    │  │    Store     │  │     APIs     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction

```
┌──────────────┐
│   FastAPI    │  Main application entry point
│ Application  │  Configures middleware, routes, lifespan
└──────┬───────┘
       │
       ├─────► ┌───────────────┐
       │       │   CORS        │  Cross-Origin Resource Sharing
       │       │  Middleware   │
       │       └───────────────┘
       │
       ├─────► ┌───────────────┐
       │       │    GZip       │  Response compression
       │       │  Middleware   │
       │       └───────────────┘
       │
       ├─────► ┌───────────────┐
       │       │  Rate Limit   │  Request throttling
       │       │  Middleware   │
       │       └───────────────┘
       │
       ├─────► ┌───────────────┐
       │       │   Timeout     │  Request timeout handling
       │       │  Middleware   │
       │       └───────────────┘
       │
       └─────► ┌───────────────┐
               │  API Routes   │  Request handlers
               └───────┬───────┘
                       │
                       ├─────► ┌──────────────┐
                       │       │   Database   │
                       │       └──────────────┘
                       │
                       └─────► ┌──────────────┐
                               │    Cache     │
                               └──────────────┘
```

---

## Component Architecture

### 1. Core Components

#### Configuration Management (`app/core/config.py`)

```python
Settings (Pydantic BaseSettings)
├── Environment variables
├── Type validation
├── Default values
└── Computed properties
```

**Design Decisions:**
- Uses Pydantic Settings for type-safe configuration
- Environment variable support for 12-factor app compliance
- Validation at startup prevents runtime errors
- Immutable configuration prevents accidental changes

#### Logging (`app/core/logging.py`)

```python
Structured Logging
├── structlog for structured output
├── JSON formatting for production
├── Console formatting for development
├── Request ID tracking
└── Context propagation
```

**Benefits:**
- Machine-readable logs for aggregation
- Correlation IDs for request tracing
- Different formats for different environments
- Performance-optimized

#### Security (`app/core/security.py`)

```python
Security Layer
├── Password hashing (bcrypt)
├── JWT token generation/verification
├── Token expiration handling
└── Password strength validation
```

### 2. Database Layer

#### In-Memory Database (`app/db/memory.py`)

```python
InMemoryDatabase
├── Collections (Dict[str, Dict[int, Dict]])
├── Locks per collection (asyncio.Lock)
├── ID generation (atomic increment)
├── CRUD operations
├── Transaction support
└── Query methods
```

**Thread Safety:**
- One lock per collection for fine-grained concurrency
- Async locks for async/await compatibility
- Atomic operations for ID generation
- Copy-on-read for data isolation

**Architecture Diagram:**

```
┌─────────────────────────────────────────┐
│       InMemoryDatabase                  │
├─────────────────────────────────────────┤
│  _data: Dict[collection, Dict[id, obj]] │
│  _locks: Dict[collection, asyncio.Lock] │
│  _id_counters: Dict[collection, int]    │
└────────────┬────────────────────────────┘
             │
             ├──► create(collection, data)
             │    ├── Acquire lock
             │    ├── Generate ID
             │    ├── Store data
             │    └── Release lock
             │
             ├──► read(collection, id)
             │    ├── Acquire lock
             │    ├── Copy data
             │    └── Release lock
             │
             ├──► update(collection, id, data)
             │    └── Merge with existing data
             │
             └──► delete(collection, id)
                  └── Remove from collection
```

### 3. Cache Layer

#### Cache Service (`app/services/cache.py`)

```python
CacheService
├── Memory store (Dict)
├── TTL support (expiration timestamps)
├── Decorator (@cache_result)
├── Pattern-based invalidation
├── Statistics tracking
└── Automatic cleanup
```

**Features:**
- Time-based expiration
- LRU eviction (when memory limit reached)
- Decorator for easy caching
- Pattern matching for bulk invalidation
- Hit/miss statistics

**Cache Flow:**

```
Request ──► Check Cache ──► Hit? ──► Return cached value
                  │
                  │ Miss
                  ▼
            Execute function ──► Store in cache ──► Return value
                                      │
                                      ▼
                              Set expiration time
```

### 4. API Layer

#### Route Organization

```
app/api/routes/
├── crud.py           # Standard CRUD operations
│   ├── POST /users           (Create)
│   ├── GET /users/{id}       (Read)
│   ├── GET /users            (List with filters)
│   ├── PUT /users/{id}       (Full update)
│   ├── PATCH /users/{id}     (Partial update)
│   ├── DELETE /users/{id}    (Delete)
│   ├── HEAD /users/{id}      (Check existence)
│   └── OPTIONS /users/{id}   (Get allowed methods)
│
├── advanced.py       # Advanced patterns
│   ├── WebSocket /ws/chat
│   ├── SSE /sse/stream
│   ├── GET /async-demo
│   ├── GET /blocking-demo
│   ├── POST /cpu-intensive
│   ├── Event Bus endpoints
│   └── Streaming endpoints
│
└── health.py         # Monitoring
    ├── GET /health
    ├── GET /health/detailed
    ├── GET /metrics
    ├── GET /ready
    └── GET /live
```

---

## Design Patterns

### 1. Repository Pattern

**Location:** `app/db/memory.py`

```python
class InMemoryDatabase:
    """Repository for data access abstraction."""
    
    async def create(self, collection: str, data: dict):
        """Create operation abstracted from storage details."""
        pass
```

**Benefits:**
- Decouples business logic from data storage
- Easy to swap implementations (in-memory → PostgreSQL)
- Testable with mock repositories

### 2. Singleton Pattern

**Location:** `app/db/memory.py`, `app/services/cache.py`

```python
_db_instance = None

async def get_db() -> InMemoryDatabase:
    """Singleton access to database."""
    global _db_instance
    if _db_instance is None:
        _db_instance = InMemoryDatabase()
    return _db_instance
```

**Rationale:**
- Single source of truth for data
- Resource conservation (one database instance)
- Simplified testing (easy to reset)

### 3. Decorator Pattern

**Location:** `app/services/cache.py`

```python
@cache_result(ttl=300)
async def expensive_operation(param: str):
    """Caching behavior added via decorator."""
    pass
```

**Benefits:**
- Separation of concerns (caching vs business logic)
- Reusable across functions
- Easy to enable/disable

### 4. Observer Pattern (Event Bus)

**Location:** `app/api/routes/advanced.py`

```python
class EventBus:
    def subscribe(self, event_type: str, handler):
        """Subscribe to events."""
        pass
    
    async def publish(self, event_type: str, data: dict):
        """Notify all subscribers."""
        pass
```

**Use Cases:**
- User creation events
- Order processing events
- Audit logging
- Real-time notifications

### 5. Circuit Breaker Pattern

**Location:** `app/middleware/resilience.py`

```python
class CircuitBreaker:
    """States: CLOSED → OPEN → HALF_OPEN → CLOSED"""
    
    async def __aenter__(self):
        if self.state == "OPEN":
            raise CircuitBreakerOpenError()
```

**Protection:**
- Prevents cascading failures
- Fast failure when service is down
- Automatic recovery attempts

### 6. Middleware Chain Pattern

**Location:** `app/main.py`

```python
app.add_middleware(CORSMiddleware)       # Layer 1
app.add_middleware(GZipMiddleware)       # Layer 2
app.add_middleware(RequestLogMiddleware) # Layer 3
app.add_middleware(RateLimitMiddleware)  # Layer 4
```

**Request Flow:**
```
Request → CORS → GZip → RequestLog → RateLimit → Route Handler
           ↓      ↓       ↓           ↓            ↓
Response ← CORS ← GZip ← RequestLog ← RateLimit ← Handler
```

---

## Data Flow

### Request Processing Flow

```
1. Client Request
   │
   ▼
2. ASGI Server (Uvicorn)
   │
   ▼
3. FastAPI Application
   │
   ├─► CORS Middleware
   ├─► GZip Middleware
   ├─► Logging Middleware
   ├─► Metrics Middleware
   ├─► Rate Limit Middleware
   └─► Timeout Middleware
   │
   ▼
4. Router
   │
   ├─► Path matching
   ├─► HTTP method matching
   └─► Parameter extraction
   │
   ▼
5. Request Validation
   │
   ├─► Path parameters (Pydantic)
   ├─► Query parameters (Pydantic)
   └─► Request body (Pydantic)
   │
   ▼
6. Route Handler
   │
   ├─► Check cache
   │   ├─► Cache hit → Return cached response
   │   └─► Cache miss → Continue
   │
   ├─► Business logic execution
   │   ├─► Database operations
   │   ├─► External API calls (thread pool)
   │   └─► CPU-intensive tasks (process pool)
   │
   └─► Response preparation
   │
   ▼
7. Response Validation
   │
   └─► Pydantic response model
   │
   ▼
8. Middleware (reverse order)
   │
   ├─► Timeout check
   ├─► Rate limit headers
   ├─► Metrics collection
   ├─► Logging
   ├─► GZip compression
   └─► CORS headers
   │
   ▼
9. ASGI Server
   │
   ▼
10. Client Response
```

### WebSocket Flow

```
1. Client WebSocket Upgrade Request
   │
   ▼
2. FastAPI WebSocket Accept
   │
   ▼
3. Connection Manager
   │
   ├─► Register connection
   └─► Add to active connections
   │
   ▼
4. Message Loop
   │
   ├─► Receive message from client
   │   │
   │   ├─► Parse JSON
   │   ├─► Validate message
   │   └─► Route to handler
   │       │
   │       ├─► Broadcast to all clients
   │       ├─► Send to specific client
   │       └─► Process and respond
   │
   └─► Send message to client
       │
       └─► Serialize to JSON
   │
   ▼
5. Disconnect
   │
   ├─► Remove from active connections
   └─► Cleanup resources
```

---

## Concurrency Model

### Event Loop Architecture

```
Main Event Loop (asyncio)
│
├─► HTTP Requests (async handlers)
│   ├─► Database operations (async)
│   ├─► Cache operations (async)
│   └─► I/O operations (async)
│
├─► WebSocket Connections (async)
│   └─► Message broadcasting (async)
│
├─► Background Tasks
│   ├─► Cache cleanup
│   └─► Metrics collection
│
├─► Thread Pool Executor
│   └─► Blocking I/O operations
│       ├─► File operations
│       ├─► Legacy libraries
│       └─► External APIs (sync)
│
└─► Process Pool Executor
    └─► CPU-intensive tasks
        ├─► Data processing
        ├─► Calculations
        └─► Heavy computations
```

### Concurrency Patterns

#### 1. Async/Await (I/O-bound)

```python
async def get_user(user_id: int):
    """Non-blocking I/O operation."""
    async with db_lock:
        user = await db.read("users", user_id)
    return user
```

**When to use:**
- Database queries
- HTTP requests
- File I/O
- Any operation that waits

#### 2. Thread Pool (Blocking I/O)

```python
async def blocking_operation():
    """Offload blocking call to thread pool."""
    result = await run_in_thread_pool(sync_blocking_function)
    return result
```

**When to use:**
- Legacy synchronous libraries
- Blocking file operations
- Third-party APIs without async support

#### 3. Process Pool (CPU-bound)

```python
async def cpu_intensive_task(data):
    """Offload CPU work to separate process."""
    result = await run_in_process_pool(calculate, data)
    return result
```

**When to use:**
- Heavy calculations
- Data processing
- Machine learning inference
- Cryptographic operations

### Concurrency Control

#### Semaphore (Limit Concurrent Operations)

```python
async def gather_with_concurrency(limit, *tasks):
    """Execute tasks with concurrency limit."""
    semaphore = asyncio.Semaphore(limit)
    
    async def bounded_task(task):
        async with semaphore:
            return await task
    
    return await asyncio.gather(*[bounded_task(t) for t in tasks])
```

#### Lock (Protect Shared State)

```python
class InMemoryDatabase:
    def __init__(self):
        self._locks = {}  # One lock per collection
    
    async def create(self, collection, data):
        lock = self._get_lock(collection)
        async with lock:
            # Thread-safe operation
            pass
```

---

## Security Architecture

### Authentication Flow

```
1. User Login
   │
   ├─► Validate credentials
   │   ├─► Username/email
   │   └─► Password (bcrypt verification)
   │
   ▼
2. Generate JWT Token
   │
   ├─► Header (algorithm, type)
   ├─► Payload (user_id, expiration)
   └─► Signature (secret key)
   │
   ▼
3. Return Token to Client
   │
   └─► Client stores in localStorage/cookie

4. Subsequent Requests
   │
   ├─► Client sends token in Authorization header
   │   └─► "Bearer <token>"
   │
   ├─► Server validates token
   │   ├─► Verify signature
   │   ├─► Check expiration
   │   └─► Extract user_id
   │
   └─► Allow/Deny request
```

### Security Layers

```
┌─────────────────────────────────────────┐
│ Layer 1: Network Security               │
│ - HTTPS/TLS                             │
│ - Rate limiting                         │
│ - IP whitelisting (optional)            │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ Layer 2: Application Security           │
│ - CORS policies                         │
│ - JWT authentication                    │
│ - Input validation (Pydantic)           │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ Layer 3: Business Logic Security        │
│ - Authorization checks                  │
│ - Resource ownership validation         │
│ - Role-based access control             │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ Layer 4: Data Security                  │
│ - Password hashing                      │
│ - Sensitive data masking                │
│ - Audit logging                         │
└─────────────────────────────────────────┘
```

---

## Scalability Architecture

### Horizontal Scaling

```
┌─────────────┐
│ Load        │
│ Balancer    │
│ (ALB/Nginx) │
└──────┬──────┘
       │
       ├──────► ┌─────────────┐
       │        │ FastAPI     │
       │        │ Instance 1  │
       │        └─────────────┘
       │
       ├──────► ┌─────────────┐
       │        │ FastAPI     │
       │        │ Instance 2  │
       │        └─────────────┘
       │
       └──────► ┌─────────────┐
                │ FastAPI     │
                │ Instance N  │
                └─────────────┘
                       │
                       ▼
                ┌─────────────┐
                │  Shared     │
                │  Database   │
                └─────────────┘
```

### Kubernetes Scaling

```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

**Scaling Triggers:**
- CPU utilization > 70%
- Memory usage > 80%
- Custom metrics (requests/second)

---

## Observability Architecture

### Three Pillars of Observability

#### 1. Logging

```python
# Structured logging
logger.info(
    "user_created",
    user_id=user.id,
    email=user.email,
    request_id=request_id
)
```

**Aggregation:** CloudWatch Logs, ELK Stack, Datadog

#### 2. Metrics

```python
# Metrics collection
metrics = {
    "requests_total": counter,
    "request_duration": histogram,
    "active_connections": gauge
}
```

**Monitoring:** Prometheus, CloudWatch, Grafana

#### 3. Tracing

```python
# Distributed tracing
with tracer.start_span("database_query") as span:
    span.set_tag("collection", "users")
    result = await db.read("users", user_id)
```

**Tools:** Jaeger, X-Ray, Zipkin

### Health Check Architecture

```
┌──────────────────────────────────────────┐
│         Health Check System              │
├──────────────────────────────────────────┤
│                                          │
│  /health (Basic)                         │
│  ├─► Quick status check                 │
│  └─► Returns 200 OK or 503              │
│                                          │
│  /health/detailed (Comprehensive)        │
│  ├─► Database connectivity              │
│  ├─► Cache availability                 │
│  ├─► External service status            │
│  └─► Component health breakdown         │
│                                          │
│  /metrics (Prometheus)                   │
│  ├─► Request counters                   │
│  ├─► Response times                     │
│  ├─► Resource usage                     │
│  └─► Custom business metrics            │
│                                          │
│  /ready (K8s Readiness)                  │
│  └─► Can accept traffic?                │
│                                          │
│  /live (K8s Liveness)                    │
│  └─► Is application alive?              │
│                                          │
└──────────────────────────────────────────┘
```

---

## Technology Stack

### Core Framework
- **FastAPI 0.109.0**: Modern, high-performance web framework
- **Pydantic 2.5.3**: Data validation and settings management
- **Uvicorn 0.27.0**: Lightning-fast ASGI server

### Async Runtime
- **asyncio**: Native Python async/await support
- **aiofiles**: Async file operations

### Data Processing
- **NumPy 1.26.3**: Numerical computing
- **Pandas 2.1.4**: Data manipulation and analysis

### Security
- **python-jose**: JWT token handling
- **passlib[bcrypt]**: Password hashing

### Testing
- **pytest 7.4.4**: Testing framework
- **pytest-asyncio 0.23.3**: Async test support
- **httpx**: Async HTTP client for testing

### Deployment
- **Docker**: Containerization
- **Kubernetes**: Orchestration
- **AWS ECS**: Managed containers

---

## Conclusion

This architecture provides:
- **Scalability**: Horizontal scaling with stateless design
- **Reliability**: Circuit breakers, retries, health checks
- **Performance**: Async I/O, caching, connection pooling
- **Maintainability**: Clean separation of concerns, type safety
- **Observability**: Comprehensive logging, metrics, tracing

For implementation details, see source code in `app/` directory.
