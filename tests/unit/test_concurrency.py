"""
Unit Tests for Concurrency Utilities

Tests async patterns, thread/process pools, and concurrency control.
"""

import pytest
import asyncio
import time
from app.utils.concurrency import (
    run_in_thread_pool,
    run_in_process_pool,
    gather_with_concurrency,
    async_retry,
    cpu_intensive_calculation
)


# ==================== THREAD POOL TESTS ====================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_in_thread_pool_basic():
    """Test running blocking function in thread pool."""
    def blocking_task(x: int) -> int:
        time.sleep(0.1)  # Simulate blocking I/O
        return x * 2
    
    result = await run_in_thread_pool(blocking_task, 5)
    
    assert result == 10


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_in_thread_pool_concurrent():
    """Test running multiple tasks concurrently in thread pool."""
    def blocking_task(x: int) -> int:
        time.sleep(0.1)
        return x * 2
    
    start_time = time.time()
    
    # Run 5 tasks concurrently
    tasks = [run_in_thread_pool(blocking_task, i) for i in range(5)]
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start_time
    
    assert results == [0, 2, 4, 6, 8]
    # Should take ~0.1s (concurrent), not 0.5s (sequential)
    assert elapsed < 0.3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_in_thread_pool_with_exception():
    """Test thread pool handles exceptions."""
    def failing_task():
        raise ValueError("Task failed!")
    
    with pytest.raises(ValueError, match="Task failed!"):
        await run_in_thread_pool(failing_task)


# ==================== PROCESS POOL TESTS ====================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_in_process_pool_basic():
    """Test running CPU-intensive function in process pool."""
    result = await run_in_process_pool(cpu_intensive_calculation, 1000000)
    
    assert isinstance(result, float)
    assert result > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_in_process_pool_concurrent():
    """Test running multiple CPU-intensive tasks in process pool."""
    start_time = time.time()
    
    # Run multiple CPU-intensive tasks
    tasks = [
        run_in_process_pool(cpu_intensive_calculation, 500000)
        for _ in range(4)
    ]
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start_time
    
    assert len(results) == 4
    assert all(isinstance(r, float) for r in results)
    print(f"\nProcess pool execution time: {elapsed:.3f}s")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cpu_intensive_calculation():
    """Test CPU-intensive calculation function."""
    result = await run_in_process_pool(cpu_intensive_calculation, 100000)
    
    assert isinstance(result, float)


# ==================== CONCURRENCY CONTROL TESTS ====================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_gather_with_concurrency_limit():
    """Test limiting concurrent operations."""
    call_count = 0
    max_concurrent = 0
    current_concurrent = 0
    
    async def tracked_task(delay: float):
        nonlocal call_count, max_concurrent, current_concurrent
        
        current_concurrent += 1
        max_concurrent = max(max_concurrent, current_concurrent)
        call_count += 1
        
        await asyncio.sleep(delay)
        
        current_concurrent -= 1
        return call_count
    
    # Create 10 tasks with max concurrency of 3
    tasks = [tracked_task(0.1) for _ in range(10)]
    results = await gather_with_concurrency(3, *tasks)
    
    assert len(results) == 10
    assert call_count == 10
    assert max_concurrent <= 3  # Should never exceed limit


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gather_with_concurrency_preserves_order():
    """Test that results maintain order despite concurrency."""
    async def indexed_task(index: int):
        await asyncio.sleep(0.01)
        return index
    
    tasks = [indexed_task(i) for i in range(20)]
    results = await gather_with_concurrency(5, *tasks)
    
    assert results == list(range(20))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gather_with_concurrency_handles_exceptions():
    """Test concurrency control handles exceptions."""
    async def failing_task(should_fail: bool):
        await asyncio.sleep(0.01)
        if should_fail:
            raise ValueError("Task failed!")
        return "success"
    
    tasks = [
        failing_task(False),
        failing_task(True),
        failing_task(False)
    ]
    
    with pytest.raises(ValueError, match="Task failed!"):
        await gather_with_concurrency(2, *tasks)


# ==================== RETRY DECORATOR TESTS ====================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_retry_success_first_try():
    """Test retry decorator when function succeeds on first try."""
    call_count = 0
    
    @async_retry(max_attempts=3, delay=0.1)
    async def successful_task():
        nonlocal call_count
        call_count += 1
        return "success"
    
    result = await successful_task()
    
    assert result == "success"
    assert call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_retry_success_after_failures():
    """Test retry decorator succeeds after initial failures."""
    call_count = 0
    
    @async_retry(max_attempts=3, delay=0.1)
    async def eventually_successful():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Not yet!")
        return "success"
    
    result = await eventually_successful()
    
    assert result == "success"
    assert call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_retry_exhausts_attempts():
    """Test retry decorator fails after exhausting attempts."""
    call_count = 0
    
    @async_retry(max_attempts=3, delay=0.1)
    async def always_fails():
        nonlocal call_count
        call_count += 1
        raise ValueError("Always fails!")
    
    with pytest.raises(ValueError, match="Always fails!"):
        await always_fails()
    
    assert call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_retry_with_exponential_backoff():
    """Test retry with exponential backoff."""
    call_times = []
    
    @async_retry(max_attempts=4, delay=0.1, exponential_backoff=True)
    async def failing_task():
        call_times.append(time.time())
        raise ValueError("Failed!")
    
    with pytest.raises(ValueError):
        await failing_task()
    
    # Verify exponential backoff delays
    assert len(call_times) == 4
    
    # Calculate delays between calls
    delays = [call_times[i+1] - call_times[i] for i in range(len(call_times)-1)]
    
    # Each delay should be roughly double the previous
    # (allowing for some variance due to execution time)
    for i in range(len(delays)-1):
        assert delays[i+1] > delays[i] * 1.5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_retry_with_custom_exceptions():
    """Test retry only on specific exceptions."""
    call_count = 0
    
    @async_retry(max_attempts=3, delay=0.1, retry_exceptions=(ValueError,))
    async def task_with_different_errors():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("Retryable error")
        elif call_count == 2:
            raise TypeError("Non-retryable error")
    
    # Should raise TypeError without retrying after it
    with pytest.raises(TypeError, match="Non-retryable error"):
        await task_with_different_errors()
    
    assert call_count == 2  # ValueError retried once, then TypeError raised


# ==================== ASYNC CONTEXT MANAGER TESTS ====================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_context_manager():
    """Test async context manager functionality."""
    from app.utils.concurrency import AsyncContextManager
    
    setup_called = False
    cleanup_called = False
    
    async def setup():
        nonlocal setup_called
        setup_called = True
        return "resource"
    
    async def cleanup(resource):
        nonlocal cleanup_called
        cleanup_called = True
    
    async with AsyncContextManager(setup, cleanup) as resource:
        assert resource == "resource"
        assert setup_called is True
        assert cleanup_called is False
    
    # After exiting context, cleanup should be called
    assert cleanup_called is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_context_manager_with_exception():
    """Test async context manager cleanup on exception."""
    cleanup_called = False
    
    async def setup():
        return "resource"
    
    async def cleanup(resource):
        nonlocal cleanup_called
        cleanup_called = True
    
    with pytest.raises(ValueError):
        async with AsyncContextManager(setup, cleanup) as resource:
            raise ValueError("Error in context!")
    
    # Cleanup should still be called
    assert cleanup_called is True


# ==================== PERFORMANCE TESTS ====================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_vs_blocking_performance():
    """Compare async vs blocking performance."""
    
    # Blocking version
    def blocking_sleep(duration: float):
        time.sleep(duration)
        return duration
    
    # Test blocking (sequential)
    start = time.time()
    blocking_results = [blocking_sleep(0.1) for _ in range(5)]
    blocking_time = time.time() - start
    
    # Test async with thread pool (concurrent)
    start = time.time()
    async_tasks = [run_in_thread_pool(blocking_sleep, 0.1) for _ in range(5)]
    async_results = await asyncio.gather(*async_tasks)
    async_time = time.time() - start
    
    print(f"\nBlocking time: {blocking_time:.3f}s")
    print(f"Async time: {async_time:.3f}s")
    print(f"Speedup: {blocking_time / async_time:.2f}x")
    
    assert len(async_results) == 5
    # Async should be significantly faster
    assert async_time < blocking_time * 0.5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limiting_pattern():
    """Test implementing rate limiting with semaphore."""
    max_concurrent = 3
    active_count = 0
    max_active = 0
    
    async def rate_limited_task():
        nonlocal active_count, max_active
        
        active_count += 1
        max_active = max(max_active, active_count)
        
        await asyncio.sleep(0.1)
        
        active_count -= 1
        return True
    
    # Run many tasks with concurrency limit
    tasks = [rate_limited_task() for _ in range(20)]
    results = await gather_with_concurrency(max_concurrent, *tasks)
    
    assert len(results) == 20
    assert max_active <= max_concurrent


@pytest.mark.unit
@pytest.mark.asyncio
async def test_task_timeout():
    """Test implementing task timeout."""
    async def slow_task():
        await asyncio.sleep(5)
        return "completed"
    
    # Task should timeout after 1 second
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(slow_task(), timeout=1.0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_task_cancellation():
    """Test cancelling async tasks."""
    cancel_event = asyncio.Event()
    
    async def cancellable_task():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancel_event.set()
            raise
    
    task = asyncio.create_task(cancellable_task())
    
    # Cancel after short delay
    await asyncio.sleep(0.1)
    task.cancel()
    
    # Wait for cancellation to be processed
    await asyncio.sleep(0.1)
    
    assert cancel_event.is_set()
    assert task.cancelled()
