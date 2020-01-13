"""Contains test utilities"""

import asyncio
from typing import Any, Callable


def async_test(async_test_func: Callable[..., None]) -> Callable[..., None]:
    """Decorator for running an async test function synchronously

    This may be useful when testing coroutines or db calls with aiopg

    Args:
        async_test_func: a test function written as a coroutine

    Returns:
        the decorated function

    """

    def sync_test_func(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(async_test_func(*args, **kwargs))

    return sync_test_func


def create_future_method(
    func: Callable[..., Any], future_return_value: Any = None
) -> Callable[..., Callable]:
    """Takes a function and makes the return an asyncio Future

    This is useful when mocking functions that are awaited when called.

    Args:
        func: a function that will be returned that itself will return a
            Future when called
        future_return_value: either the value the future should return or the
            exception it should raise when run to completion

    Returns:
        the original function with a return of a Future.

    """
    f = asyncio.Future()

    if isinstance(future_return_value, Exception):
        f.set_exception(future_return_value)
    else:
        f.set_result(future_return_value)

    func.return_value = f
    return func
