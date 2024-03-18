from typing import Any
import os
from contextlib import contextmanager

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from filelock import FileLock

@contextmanager
def id_lock (id: Any, lock_dir: str, timeout: float = -1):
    if not os.path.exists(lock_dir):
        os.makedirs(lock_dir)
    lock = FileLock(os.path.join(lock_dir, f'{id}.lock'), thread_local=False, timeout=timeout)
    try:
        lock.acquire()
        yield
    finally:
        lock.release()

@contextmanager
def timeout(seconds: float):
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(lambda: None)  # Submit an empty task
        future.result(timeout=seconds)  # Wait for task completion or timeout
        yield
    except TimeoutError:
        raise
    finally:
        executor.shutdown(wait=False)