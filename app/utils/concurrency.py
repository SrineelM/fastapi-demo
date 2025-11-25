"""
Concurrency Utilities Module

This module demonstrates various concurrency patterns in Python:
- Async/await patterns
- Thread pool execution
- Process pool execution  
- Semaphores and locks
- Concurrent task management

Key Concepts:
- asyncio for I/O-bound operations
- ThreadPoolExecutor for blocking I/O
- ProcessPoolExecutor for CPU-bound operations
- Proper resource cleanup

Usage:
    from app.utils.concurrency import (
        run_in_thread_pool,
        run_in_process_pool,
        gather_with_concurrency
    )
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Any, Callable, List, TypeVar, Coroutine
from functools import wraps, partial
import time
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')

# Global thread pool for blocking operations
# Size is based on expected concurrent blocking operations
_thread_pool: ThreadPoolExecutor | None = None
_process_pool: ProcessPoolExecutor | None = None


def get_thread_pool() -> ThreadPoolExecutor:
    """
    Get or create the global thread pool.
    
    Thread pools are used for blocking I/O operations that can't use asyncio.
    Examples: file I/O, database operations without async drivers, third-party APIs.
    
    Returns:
        ThreadPoolExecutor instance
        
    Example:
        >>> pool = get_thread_pool()
        >>> loop = asyncio.get_event_loop()
        >>> result = await loop.run_in_executor(pool, blocking_function, arg1, arg2)
    """
    global _thread_pool
    if _thread_pool is None:
        # Use 4x CPU count for I/O-bound operations
        import os
        max_workers = (os.cpu_count() or 1) * 4
        _thread_pool = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="fastapi_worker"
        )
        logger.info("Thread pool initialized", max_workers=max_workers)
    return _thread_pool


def get_process_pool() -> ProcessPoolExecutor:
    """
    Get or create the global process pool.
    
    Process pools are used for CPU-bound operations that benefit from
    parallel processing. Each process has its own Python interpreter.
    
    Returns:
        ProcessPoolExecutor instance
        
    Example:
        >>> pool = get_process_pool()
        >>> loop = asyncio.get_event_loop()
        >>> result = await loop.run_in_executor(pool, cpu_intensive_function, data)
    """
    global _process_pool
    if _process_pool is None:
        # Use CPU count for CPU-bound operations
        import os
        max_workers = os.cpu_count() or 1
        _process_pool = ProcessPoolExecutor(
            max_workers=max_workers
        )
        logger.info("Process pool initialized", max_workers=max_workers)
    return _process_pool


async def run_in_thread_pool(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Run a blocking function in a thread pool.
    
    This is useful for integrating blocking code (like synchronous database
    calls or file I/O) with async code.
    
    Args:
        func: Blocking function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        Function result
        
    Example:
        >>> def blocking_api_call(url):
        >>>     import requests
        >>>     return requests.get(url).json()
        >>> 
        >>> result = await run_in_thread_pool(blocking_api_call, "https://api.example.com")
    """
    loop = asyncio.get_event_loop()
    pool = get_thread_pool()
    
    # Use partial to handle keyword arguments
    func_with_args = partial(func, *args, **kwargs) if kwargs else partial(func, *args)
    
    logger.debug("Running function in thread pool", function=func.__name__)
    start_time = time.time()
    
    result = await loop.run_in_executor(pool, func_with_args)
    
    duration_ms = (time.time() - start_time) * 1000
    logger.debug(
        "Thread pool execution completed",
        function=func.__name__,
        duration_ms=round(duration_ms, 2)
    )
    
    return result


async def run_in_process_pool(func: Callable[..., T], *args: Any) -> T:
    """
    Run a CPU-intensive function in a process pool.
    
    Use this for computationally expensive operations like:
    - Data processing with NumPy/Pandas
    - Image/video processing
    - Complex calculations
    
    Note: The function and arguments must be picklable.
    
    Args:
        func: CPU-intensive function to execute
        *args: Positional arguments for the function
        
    Returns:
        Function result
        
    Example:
        >>> def process_large_dataset(data):
        >>>     import numpy as np
        >>>     return np.mean(data)
        >>> 
        >>> result = await run_in_process_pool(process_large_dataset, large_array)
    """
    loop = asyncio.get_event_loop()
    pool = get_process_pool()
    
    logger.debug("Running function in process pool", function=func.__name__)
    start_time = time.time()
    
    result = await loop.run_in_executor(pool, func, *args)
    
    duration_ms = (time.time() - start_time) * 1000
    logger.debug(
        "Process pool execution completed",
        function=func.__name__,
        duration_ms=round(duration_ms, 2)
    )
    
    return result


async def gather_with_concurrency(
    n: int,
    *tasks: Coroutine[Any, Any, T]
) -> List[T]:
    """
    Run multiple async tasks with limited concurrency.
    
    This prevents overwhelming the system with too many concurrent operations.
    Uses a semaphore to limit the number of tasks running simultaneously.
    
    Args:
        n: Maximum number of concurrent tasks
        *tasks: Coroutines to execute
        
    Returns:
        List of results in the same order as input tasks
        
    Example:
        >>> tasks = [fetch_user(id) for id in range(100)]
        >>> results = await gather_with_concurrency(10, *tasks)
    """
    semaphore = asyncio.Semaphore(n)
    
    async def sem_task(task: Coroutine[Any, Any, T]) -> T:
        async with semaphore:
            return await task
    
    logger.debug("Gathering tasks with concurrency", concurrency=n, total_tasks=len(tasks))
    return await asyncio.gather(*[sem_task(task) for task in tasks])


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator to retry async functions with exponential backoff.
    
    Implements resilience pattern for transient failures.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each attempt
        exceptions: Tuple of exceptions to catch and retry
        
    Returns:
        Decorator function
        
    Example:
        >>> @async_retry(max_attempts=3, delay=1.0, backoff=2.0)
        >>> async def flaky_api_call():
        >>>     # May fail occasionally
        >>>     return await external_api.get_data()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        logger.error(
                            "Max retry attempts reached",
                            function=func.__name__,
                            attempts=max_attempts,
                            error=str(e)
                        )
                        raise
                    
                    logger.warning(
                        "Retry attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_attempts=max_attempts,
                        delay=current_delay,
                        error=str(e)
                    )
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            return None  # Should never reach here
        
        return wrapper
    return decorator


class AsyncContextManager:
    """
    Example async context manager for resource management.
    
    Demonstrates proper async context manager implementation
    with __aenter__ and __aexit__ methods.
    
    Example:
        >>> async with AsyncContextManager("database") as resource:
        >>>     # Use resource
        >>>     await resource.query("SELECT * FROM users")
    """
    
    def __init__(self, resource_name: str):
        self.resource_name = resource_name
        self.is_acquired = False
        logger.debug("Context manager created", resource=resource_name)
    
    async def __aenter__(self) -> "AsyncContextManager":
        """Acquire resource on context entry."""
        logger.info("Acquiring resource", resource=self.resource_name)
        # Simulate async resource acquisition
        await asyncio.sleep(0.1)
        self.is_acquired = True
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Release resource on context exit."""
        logger.info(
            "Releasing resource",
            resource=self.resource_name,
            exception_occurred=exc_type is not None
        )
        # Simulate async resource cleanup
        await asyncio.sleep(0.1)
        self.is_acquired = False


async def shutdown_executors() -> None:
    """
    Shutdown thread and process pools.
    
    Call this during application shutdown to properly cleanup resources.
    """
    global _thread_pool, _process_pool
    
    if _thread_pool:
        _thread_pool.shutdown(wait=True)
        _thread_pool = None
        logger.info("Thread pool shutdown")
    
    if _process_pool:
        _process_pool.shutdown(wait=True)
        _process_pool = None
        logger.info("Process pool shutdown")


# Example CPU-bound function for process pool
def cpu_intensive_calculation(n: int) -> int:
    """
    Example CPU-intensive calculation.
    
    This demonstrates a function suitable for process pool execution.
    
    Args:
        n: Input value
        
    Returns:
        Calculated result
    """
    # Simulate heavy computation (calculating fibonacci)
    def fib(x: int) -> int:
        if x <= 1:
            return x
        return fib(x - 1) + fib(x - 2)
    
    return fib(min(n, 35))  # Cap at 35 to avoid excessive computation


# Example blocking I/O function for thread pool
def blocking_io_operation(filepath: str) -> str:
    """
    Example blocking I/O operation.
    
    This demonstrates a function suitable for thread pool execution.
    
    Args:
        filepath: File path to read
        
    Returns:
        File contents
    """
    time.sleep(0.1)  # Simulate I/O delay
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return ""
