from functools import wraps
import inspect
import time
from typing import Callable


def time_it(log_fn: Callable[[str], None]):
    def decorator(func):
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                log_fn(f"Starting '{func.__name__}'")
                start = time.perf_counter()
                result = await func(*args, **kwargs)
                end = time.perf_counter()
                log_fn(f"Finished '{func.__name__}' in {end - start:.6f} seconds")

                return result

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                log_fn(f"Starting '{func.__name__}'")
                start = time.perf_counter()
                result = func(*args, **kwargs)
                end = time.perf_counter()
                log_fn(f"Finished '{func.__name__}' in {end - start:.6f} seconds")

                return result

            return sync_wrapper

    return decorator
