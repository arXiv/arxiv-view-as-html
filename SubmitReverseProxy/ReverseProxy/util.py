import tarfile
import shutil
import os
import logging

from .config import SITES_DIR, TARS_DIR

def untar(id: int) -> str:
    with tarfile.open(f'{TARS_DIR}{id}') as tar:
        tar.extractall(SITES_DIR)
        tar.close()
    return f'{SITES_DIR}{id}'

def clean_up (id: int) -> bool:
    try:
        shutil.rmtree(f'{SITES_DIR}{id}')
        os.remove(f'{TARS_DIR}{id}')
        return True
    except:
        return False
