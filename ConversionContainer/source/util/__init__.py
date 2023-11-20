from typing import Any, Tuple, Optional
from contextlib import contextmanager
import os
import shutil
import tarfile
import gzip
import re

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from filelock import FileLock

# # arXiv ID format used from 1991 to 2007-03
# RE_ARXIV_OLD_ID = re.compile(
#     r'^(?P<archive>[a-z]{1,}(\-[a-z]{2,})?)(\.([a-zA-Z\-]{2,}))?\/'
#     r'(?P<yymm>(?P<yy>\d\d)(?P<mm>\d\d))(?P<num>\d\d\d)'
#     r'(v(?P<version>[1-9]\d*))?(?P<extra>[#\/].*)?$')

# # arXiv ID format used from 2007-04 to present
# RE_ARXIV_NEW_ID = re.compile(
#     r'^(?P<yymm>(?P<yy>\d\d)(?P<mm>\d\d))\.(?P<num>\d{4,5})'
#     r'(v(?P<version>[1-9]\d*))?(?P<extra>[#\/].*)?$'
# )

# def get_arxiv_id_from_blob (blob: str) -> Optional[Tuple[str, bool]]:
#     """ 
#     Returns a tuple containing the arxiv_id and whether 
#     or not it's a new format id or None if there's no match
#     """
#     if (match := re.search(RE_ARXIV_NEW_ID, blob)):
#         return match.group(), True
#     elif (match := re.search(RE_ARXIV_OLD_ID, blob)):
#         return match.group(), False
#     else:
#         return None

def untar (fpath: str, dir_name: str):
    with tarfile.open(fpath) as tar:
        tar.extractall(dir_name)
        tar.close()

def unzip_single_file (fpath: str, dir_name: str):
    fname = f'{os.path.basename(fpath)[:-3]}.tex'
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