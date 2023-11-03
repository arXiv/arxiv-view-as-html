from typing import Any
from contextlib import contextmanager
import os
import shutil
import tarfile
import gzip

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from filelock import FileLock

def untar (fpath: str, dir_name: str):
    with tarfile.open(fpath) as tar:
        tar.extractall(dir_name)
        tar.close()

def unzip_single_file (fpath: str, dir_name: str):
    fname = os.path.basename(fpath)[:-3]
    with gzip.open(fpath) as ungzip:
        with open(os.path.join(dir_name, fname), 'wb+') as out:
            shutil.copyfileobj(ungzip, out)

@contextmanager
def id_lock (id: Any, lock_dir: str, timeout: float = -1) -> FileLock:
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