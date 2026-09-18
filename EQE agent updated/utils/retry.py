"""Async-safe retry decorator for Playwright operations.

Usage:
    @async_retry(max_attempts=3, delay_sec=1.0, exceptions=(AssertionError,))
    async def flaky_operation():
        ...

Also exported as a context-aware helper for page-level calls:
    result = await retry_async(some_coroutine_func, args=(arg1,), attempts=3)
"""
from __future__ import annotations

import asyncio
import functools
import logging
from typing import Any, Callable, Coroutine, Sequence, Tuple, Type

logger = logging.getLogger("retry")


def async_retry(
    max_attempts: int = 3,
    delay_sec: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """Decorator: retry an async function up to *max_attempts* times on specified exceptions.

    Args:
        max_attempts: Total number of tries (including first attempt).
        delay_sec:    Seconds to wait before the first retry.
        backoff:      Multiplier applied to delay_sec after each failure.
        exceptions:   Tuple of exception types that trigger a retry.
    """
    def decorator(func: Callable[..., Coroutine]) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            wait = delay_sec
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        logger.error(
                            "[retry] %s failed after %d attempts: %s",
                            func.__name__, max_attempts, exc,
                        )
                        raise
                    logger.warning(
                        "[retry] %s attempt %d/%d failed (%s). Retrying in %.1fs…",
                        func.__name__, attempt, max_attempts, exc, wait,
                    )
                    await asyncio.sleep(wait)
                    wait *= backoff
        return wrapper
    return decorator


async def retry_async(
    coro_func: Callable[..., Coroutine],
    args: Sequence[Any] = (),
    kwargs: dict | None = None,
    max_attempts: int = 3,
    delay_sec: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Any:
    """Functional retry wrapper — useful when you cannot use the decorator."""
    kwargs = kwargs or {}
    wait = delay_sec

    for attempt in range(1, max_attempts + 1):
        try:
            return await coro_func(*args, **kwargs)
        except exceptions as exc:
            if attempt == max_attempts:
                raise
            logger.warning(
                "[retry] attempt %d/%d failed (%s). Retrying in %.1fs…",
                attempt, max_attempts, exc, wait,
            )
            await asyncio.sleep(wait)
            wait *= backoff


def sync_retry(
    max_attempts: int = 3,
    delay_sec: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """Decorator: retry a sync function up to *max_attempts* times on specified exceptions."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            import time

            wait = delay_sec
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        logger.error(
                            "[retry] %s failed after %d attempts: %s",
                            func.__name__, max_attempts, exc,
                        )
                        raise
                    logger.warning(
                        "[retry] %s attempt %d/%d failed (%s). Retrying in %.1fs…",
                        func.__name__, attempt, max_attempts, exc, wait,
                    )
                    time.sleep(wait)
                    wait *= backoff

        return wrapper

    return decorator


def retry_sync(
    func: Callable[..., Any],
    args: Sequence[Any] = (),
    kwargs: dict | None = None,
    max_attempts: int = 3,
    delay_sec: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Any:
    """Functional retry wrapper for sync operations."""

    import time

    kwargs = kwargs or {}
    wait = delay_sec

    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except exceptions as exc:
            if attempt == max_attempts:
                raise
            logger.warning(
                "[retry] attempt %d/%d failed (%s). Retrying in %.1fs…",
                attempt, max_attempts, exc, wait,
            )
            time.sleep(wait)
            wait *= backoff
