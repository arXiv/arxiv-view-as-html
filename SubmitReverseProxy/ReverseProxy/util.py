import tarfile
import shutil
import os
import logging

from .config import SITES_DIR, TARS_DIR

def untar(id, conference_proceeding: bool = False) -> str:
    with tarfile.open(f'{TARS_DIR}{id}') as tar:
        if conference_proceeding:
            tar.extractall(f'{SITES_DIR}{id}') # These aren't in a folder
        else:
            tar.extractall(SITES_DIR)
        tar.close()
    logging.info(os.listdir(SITES_DIR))
    logging.info(os.listdir(f'{SITES_DIR}{id}'))
    return f'{SITES_DIR}{id}'

def clean_up (id: int) -> bool:
    try:
        shutil.rmtree(f'{SITES_DIR}{id}')
        os.remove(f'{TARS_DIR}{id}')
        return True
    except:
        return False
