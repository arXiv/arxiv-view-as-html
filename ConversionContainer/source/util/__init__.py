from typing import Any
from contextlib import contextmanager
import os
import tarfile

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from filelock import FileLock

from ..exceptions import TimeoutException

def untar (fpath: str, dir_name: str):
    with tarfile.open(fpath) as tar:
        tar.extractall(dir_name)
        tar.close()

@contextmanager
def id_lock (id: Any, lock_dir: str, timeout: float = -1) -> FileLock:
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