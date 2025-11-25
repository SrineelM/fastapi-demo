"""
Pytest Configuration and Fixtures

This file contains pytest configuration and reusable fixtures for testing.
Fixtures provide setup/teardown and reusable test dependencies.

Key Features:
- Async test support
- Test client setup
- Database fixtures
- Mock data generators
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from httpx import AsyncClient
from app.main import app
from app.db.memory import get_db, reset_db
from app.services.cache import get_cache


# ==================== PYTEST CONFIGURATION ====================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


# ==================== EVENT LOOP FIXTURE ====================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """
    Create event loop for async tests.
    
    This fixture provides an event loop that persists for the entire
    test session, allowing async tests to run properly.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== TEST CLIENT FIXTURES ====================

@pytest.fixture
def client() -> Generator:
    """
    Create synchronous test client.
    
    Use this for testing synchronous endpoints and basic functionality.
    
    Example:
        def test_health(client):
            response = client.get("/api/v1/health")
            assert response.status_code == 200
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def async_client():
    """
    Create asynchronous test client.
    
    Use this for testing async endpoints and WebSocket connections.
    Note: TestClient is synchronous but supports FastAPI async endpoints.
    
    Example:
        def test_async_endpoint(async_client):
            response = async_client.get("/api/v1/users")
            assert response.status_code == 200
    """
    with TestClient(app) as test_client:
        yield test_client


# ==================== DATABASE FIXTURES ====================

@pytest.fixture(autouse=True)
async def reset_database() -> AsyncGenerator[None, None]:
    """
    Reset database before each test.
    
    This fixture runs automatically before each test to ensure
    a clean database state. Prevents test interference.
    """
    await reset_db()
    yield
    await reset_db()


@pytest.fixture
async def db():
    """
    Get database instance.
    
    Provides access to the in-memory database for testing.
    """
    return get_db()


@pytest.fixture
async def cache():
    """
    Get cache instance.
    
    Provides access to the cache service for testing.
    """
    cache_instance = get_cache()
    await cache_instance.clear()  # Clear cache before test
    yield cache_instance
    await cache_instance.clear()  # Clear cache after test


# ==================== MOCK DATA FIXTURES ====================

@pytest.fixture
def sample_user_data() -> dict:
    """
    Sample user data for testing.
    
    Returns:
        Dictionary with valid user data
    """
    return {
        "name": "Test User",
        "email": "test@example.com",
        "age": 30,
        "role": "user",
        "is_active": True,
        "password": "SecurePass123"
    }


@pytest.fixture
def sample_users_data() -> list[dict]:
    """
    Multiple sample users for testing.
    
    Returns:
        List of user dictionaries
    """
    return [
        {
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "age": 28,
            "role": "admin",
            "is_active": True,
            "password": "SecurePass123"
        },
        {
            "name": "Bob Smith",
            "email": "bob@example.com",
            "age": 35,
            "role": "user",
            "is_active": True,
            "password": "SecurePass123"
        },
        {
            "name": "Charlie Brown",
            "email": "charlie@example.com",
            "age": 42,
            "role": "user",
            "is_active": False,
            "password": "SecurePass123"
        }
    ]


@pytest.fixture
def sample_product_data() -> dict:
    """
    Sample product data for testing.
    
    Returns:
        Dictionary with valid product data
    """
    return {
        "name": "Test Product",
        "description": "A test product description",
        "price": 99.99,
        "stock": 100,
        "category": "Electronics",
        "tags": ["test", "sample"]
    }


@pytest.fixture
def sample_products_data() -> list[dict]:
    """
    Multiple sample products for testing.
    
    Returns:
        List of product dictionaries
    """
    return [
        {
            "name": "Laptop",
            "description": "High-performance laptop",
            "price": 1299.99,
            "stock": 50,
            "category": "Electronics",
            "tags": ["computer", "portable"]
        },
        {
            "name": "Mouse",
            "description": "Wireless mouse",
            "price": 29.99,
            "stock": 200,
            "category": "Electronics",
            "tags": ["accessory", "wireless"]
        },
        {
            "name": "Desk Chair",
            "description": "Ergonomic office chair",
            "price": 399.99,
            "stock": 30,
            "category": "Furniture",
            "tags": ["office", "ergonomic"]
        }
    ]


# ==================== HELPER FIXTURES ====================

@pytest.fixture
async def create_test_user(db):
    """
    Factory fixture for creating test users.
    
    Returns:
        Async function that creates a user in the database
        
    Example:
        async def test_something(create_test_user):
            user = await create_test_user(name="John", email="john@example.com")
            assert user["id"] == 1
    """
    async def _create_user(**kwargs):
        user_data = {
            "name": kwargs.get("name", "Test User"),
            "email": kwargs.get("email", "test@example.com"),
            "age": kwargs.get("age", 30),
            "role": kwargs.get("role", "user"),
            "is_active": kwargs.get("is_active", True)
        }
        return await db.create("users", user_data)
    
    return _create_user


@pytest.fixture
async def create_test_product(db):
    """
    Factory fixture for creating test products.
    
    Returns:
        Async function that creates a product in the database
    """
    async def _create_product(**kwargs):
        product_data = {
            "name": kwargs.get("name", "Test Product"),
            "description": kwargs.get("description", "Test description"),
            "price": kwargs.get("price", 99.99),
            "stock": kwargs.get("stock", 100),
            "category": kwargs.get("category", "Test"),
            "tags": kwargs.get("tags", ["test"])
        }
        return await db.create("products", product_data)
    
    return _create_product


# ==================== MOCK FIXTURES ====================

@pytest.fixture
def mock_external_api(monkeypatch):
    """
    Mock external API calls.
    
    Use this to mock calls to external services during testing.
    
    Example:
        def test_with_mock(mock_external_api):
            # External API calls will be mocked
            pass
    """
    async def mock_api_call(*args, **kwargs):
        return {"status": "success", "data": "mocked"}
    
    # Monkeypatch can be used to replace functions
    # monkeypatch.setattr("module.function", mock_api_call)
    
    return mock_api_call


# ==================== PERFORMANCE FIXTURES ====================

@pytest.fixture
def benchmark_timer():
    """
    Simple benchmark timer for performance testing.
    
    Returns:
        Context manager that times code execution
        
    Example:
        def test_performance(benchmark_timer):
            with benchmark_timer() as timer:
                # Code to benchmark
                pass
            assert timer.elapsed < 1.0  # Should complete in under 1 second
    """
    import time
    from contextlib import contextmanager
    
    class Timer:
        def __init__(self):
            self.elapsed = 0
        
        @contextmanager
        def __call__(self):
            start = time.time()
            try:
                yield self
            finally:
                self.elapsed = time.time() - start
    
    return Timer()
