import pytest
import os
import shutil
import multiprocessing
import time

from conversion.locking import id_lock

def test_id_lock():
    lock_dir = "./lock_dir"
    lock_id = "2407.00113"
    timeout = 1

    success_output = 'Lock acquired'
    fail_output = 'Failed to acquire lock'

    if not os.path.exists(lock_dir):
        os.makedirs(lock_dir, exist_ok=True)

    def lock_function(lock_id: str, lock_dir: str, timeout: float, result_queue: multiprocessing.Queue):
        try:
            with id_lock(lock_id, lock_dir, timeout):
                result_queue.put(success_output)
                time.sleep(1.5)
        except Exception as e:
            result_queue.put(f'{fail_output} with {str(e)}')    

    result_queue1 = multiprocessing.Queue()
    result_queue2 = multiprocessing.Queue()

    proc1 = multiprocessing.Process(target=lock_function, args=(lock_id, lock_dir, timeout, result_queue1))
    proc1.start()

    proc2 = multiprocessing.Process(target=lock_function, args=(lock_id, lock_dir, timeout, result_queue2))
    proc2.start()

    proc1.join()
    proc2.join()

    result1 = result_queue1.get()
    result2 = result_queue2.get()

    assert result1 == success_output
    assert fail_output in result2

    try:
        shutil.rmtree(lock_dir)
    except Exception as e:
        print (f'Failed to delete {lock_dir} with {str(e)}')

def test_convert_success ():
    ...

def test_convert_success_single_file ():
    ...

def test_convert_concurrent ():
    ...

def test_convert_failure ():
    ...