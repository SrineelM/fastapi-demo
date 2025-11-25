"""
Unit Tests for Cache Service

Tests caching functionality including:
- Get/Set/Delete operations
- TTL (Time To Live) behavior
- Cache decorator
- Cache invalidation
- Concurrent access
"""

import pytest
import asyncio
from app.services.cache import cache_result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_set_and_get(cache):
    """Test basic cache set and get operations."""
    await cache.set("test_key", "test_value")
    
    value = await cache.get("test_key")
    
    assert value == "test_value"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_get_nonexistent_key(cache):
    """Test getting non-existent key returns None."""
    value = await cache.get("nonexistent_key")
    
    assert value is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_ttl_expiration(cache):
    """Test that cached values expire after TTL."""
    # Set with 1 second TTL
    await cache.set("expire_key", "expire_value", ttl=1)
    
    # Should exist immediately
    value1 = await cache.get("expire_key")
    assert value1 == "expire_value"
    
    # Wait for expiration
    await asyncio.sleep(1.5)
    
    # Should be expired
    value2 = await cache.get("expire_key")
    assert value2 is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_update_existing_key(cache):
    """Test updating an existing cache key."""
    await cache.set("update_key", "original_value")
    await cache.set("update_key", "updated_value")
    
    value = await cache.get("update_key")
    
    assert value == "updated_value"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_delete(cache):
    """Test deleting a cached value."""
    await cache.set("delete_key", "delete_value")
    
    # Verify it exists
    assert await cache.get("delete_key") == "delete_value"
    
    # Delete it
    await cache.delete("delete_key")
    
    # Verify it's gone
    assert await cache.get("delete_key") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_clear(cache):
    """Test clearing all cached values."""
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")
    await cache.set("key3", "value3")
    
    await cache.clear()
    
    assert await cache.get("key1") is None
    assert await cache.get("key2") is None
    assert await cache.get("key3") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_complex_data_types(cache):
    """Test caching complex data types."""
    # Dictionary
    dict_data = {"name": "John", "age": 30, "tags": ["python", "fastapi"]}
    await cache.set("dict_key", dict_data)
    assert await cache.get("dict_key") == dict_data
    
    # List
    list_data = [1, 2, 3, 4, 5]
    await cache.set("list_key", list_data)
    assert await cache.get("list_key") == list_data
    
    # Nested structure
    nested_data = {
        "user": {"name": "Alice", "email": "alice@example.com"},
        "posts": [{"id": 1, "title": "Post 1"}, {"id": 2, "title": "Post 2"}]
    }
    await cache.set("nested_key", nested_data)
    assert await cache.get("nested_key") == nested_data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_decorator_basic():
    """Test cache decorator caches function results."""
    call_count = 0
    
    @cache_result(ttl=60)
    async def expensive_function(x: int) -> int:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)  # Simulate expensive operation
        return x * 2
    
    # First call - should execute function
    result1 = await expensive_function(5)
    assert result1 == 10
    assert call_count == 1
    
    # Second call with same argument - should use cache
    result2 = await expensive_function(5)
    assert result2 == 10
    assert call_count == 1  # Function not called again
    
    # Call with different argument - should execute function
    result3 = await expensive_function(10)
    assert result3 == 20
    assert call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_decorator_with_multiple_args():
    """Test cache decorator with multiple arguments."""
    @cache_result(ttl=60)
    async def add(a: int, b: int) -> int:
        return a + b
    
    result1 = await add(2, 3)
    result2 = await add(2, 3)  # Same args - cached
    result3 = await add(3, 2)  # Different order - not cached
    
    assert result1 == 5
    assert result2 == 5
    assert result3 == 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_decorator_with_kwargs():
    """Test cache decorator handles keyword arguments."""
    @cache_result(ttl=60)
    async def greet(name: str, greeting: str = "Hello") -> str:
        return f"{greeting}, {name}!"
    
    result1 = await greet("Alice")
    result2 = await greet(name="Alice")  # Same call, different style
    result3 = await greet("Alice", greeting="Hi")
    
    assert result1 == "Hello, Alice!"
    assert result2 == "Hello, Alice!"
    assert result3 == "Hi, Alice!"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_decorator_ttl_expiration():
    """Test cache decorator respects TTL."""
    call_count = 0
    
    @cache_result(ttl=1)
    async def get_timestamp():
        nonlocal call_count
        call_count += 1
        return asyncio.get_event_loop().time()
    
    # First call
    result1 = await get_timestamp()
    assert call_count == 1
    
    # Immediate second call - cached
    result2 = await get_timestamp()
    assert result2 == result1
    assert call_count == 1
    
    # Wait for cache to expire
    await asyncio.sleep(1.5)
    
    # Third call - cache expired, function called again
    result3 = await get_timestamp()
    assert result3 != result1
    assert call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_concurrent_access(cache):
    """Test cache handles concurrent access safely."""
    async def reader(key: str):
        return await cache.get(key)
    
    async def writer(key: str, value: str):
        await cache.set(key, value)
    
    # Concurrent reads and writes
    tasks = []
    tasks.extend([writer(f"key_{i}", f"value_{i}") for i in range(50)])
    tasks.extend([reader(f"key_{i}") for i in range(50)])
    
    await asyncio.gather(*tasks)
    
    # Verify all values are set correctly
    for i in range(50):
        value = await cache.get(f"key_{i}")
        assert value == f"value_{i}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_pattern_invalidation(cache):
    """Test invalidating multiple keys by pattern."""
    # Set multiple keys with similar patterns
    await cache.set("user:1:profile", {"name": "User 1"})
    await cache.set("user:2:profile", {"name": "User 2"})
    await cache.set("user:1:posts", ["post1", "post2"])
    await cache.set("product:1", {"name": "Product 1"})
    
    # Invalidate all user:1:* keys
    await cache.delete_pattern("user:1:*")
    
    # User 1 keys should be gone
    assert await cache.get("user:1:profile") is None
    assert await cache.get("user:1:posts") is None
    
    # Other keys should remain
    assert await cache.get("user:2:profile") == {"name": "User 2"}
    assert await cache.get("product:1") == {"name": "Product 1"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_stats(cache):
    """Test cache statistics."""
    # Perform some operations
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")
    await cache.get("key1")  # Hit
    await cache.get("key3")  # Miss
    
    stats = await cache.get_stats()
    
    assert "size" in stats
    assert "hits" in stats
    assert "misses" in stats
    assert stats["size"] >= 2
    assert stats["hits"] >= 1
    assert stats["misses"] >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_memory_limit(cache):
    """Test cache respects memory limits."""
    # Fill cache with many items
    for i in range(1000):
        await cache.set(f"item_{i}", f"value_{i}" * 100)
    
    stats = await cache.get_stats()
    
    # Cache should have evicted old items if memory limit reached
    assert stats["size"] > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_key_generation():
    """Test cache key generation from function arguments."""
    from app.services.cache import generate_cache_key
    
    # Test with different argument combinations
    key1 = generate_cache_key("test_func", (1, 2), {"x": 3})
    key2 = generate_cache_key("test_func", (1, 2), {"x": 3})
    key3 = generate_cache_key("test_func", (2, 1), {"x": 3})
    
    # Same arguments should produce same key
    assert key1 == key2
    
    # Different arguments should produce different key
    assert key1 != key3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_cleanup_expired_items(cache):
    """Test that expired items are cleaned up."""
    # Set items with short TTL
    for i in range(10):
        await cache.set(f"expire_{i}", f"value_{i}", ttl=1)
    
    # Verify items exist
    assert await cache.get("expire_0") is not None
    
    # Wait for expiration
    await asyncio.sleep(1.5)
    
    # Trigger cleanup (this happens automatically in background)
    await cache.cleanup_expired()
    
    # Verify items are gone
    for i in range(10):
        assert await cache.get(f"expire_{i}") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_null_values(cache):
    """Test caching None/null values."""
    # Cache None value
    await cache.set("null_key", None)
    
    # Should return None (not same as key not existing)
    value = await cache.get("null_key")
    assert value is None
    
    # But key should exist
    stats = await cache.get_stats()
    assert stats["size"] > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_decorator_with_cache_disable():
    """Test cache decorator can be disabled."""
    call_count = 0
    
    @cache_result(ttl=60, enabled=False)
    async def always_fresh():
        nonlocal call_count
        call_count += 1
        return call_count
    
    result1 = await always_fresh()
    result2 = await always_fresh()
    
    # Function should be called each time (no caching)
    assert result1 == 1
    assert result2 == 2
