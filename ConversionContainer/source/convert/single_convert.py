import uuid
import os
import shutil
import logging
import traceback

from flask import current_app

from ..util import untar, id_lock
from ..buckets import download_blob, upload_dir_to_gcs
from ..exceptions import *
from .concurrency_control import (
    write_start, 
    write_success, 
    write_failure,
    has_doc_been_tried
)
from . import (
    _remove_ltxml, 
    _find_main_tex_source, 
    _do_latexml,
    _insert_missing_package_warning,
    _clean_up
)

def single_convert_process (id: str, blob: str, bucket: str) -> bool:

    """ File system we will be using """
    safe_name = str(uuid.uuid4()) # In case two machines download before locking
    tar_gz = f'{safe_name}.tar.gz' # the file we download the blob to
    src_dir = f'extracted/{id}' # the directory we untar the blob to
    bucket_dir_container = f'{src_dir}/html' # the directory we will upload the *contents* of
    outer_bucket_dir = f'{bucket_dir_container}/{id}' # the highest level directory that will appear in the out bucket

    try:
        with id_lock(id, current_app.config['LOCK_DIR']):

            try:
                os.makedirs(outer_bucket_dir)
            except OSError:
                shutil.rmtree(src_dir)
                os.makedirs(outer_bucket_dir)
                # Abort if this fails
            
            # Check file format and download to ./[{id}.tar.gz]
            try:
                logging.info(f"Step 1: Download {id}")
                download_blob(bucket, blob, tar_gz)
            except:
                logging.info(f'Failed to download {id}')
                traceback.print_exc()
                return
            
            # Write to DB that process has started
            logging.info(f"Write start process to db")
            write_start(id, tar_gz, False)
    
            # Untar file ./[tar] to ./extracted/id/
            logging.info(f"Step 2: Untar {id}")
            untar (tar_gz, src_dir)

            # Remove .ltxml files from [source] (./extracted/id/)
            logging.info(f"Step 3: Remove .ltxml for {id}")
            _remove_ltxml(src_dir)

            # Identify main .tex source in [source]
            logging.info(f"Step 4: Identify main .tex source for {id}")
            main = _find_main_tex_source(src_dir)
                
            # Run LaTeXML on main and output to ./extracted/id/html/id
            logging.info(f"Step 5: Do LaTeXML for {id}")
            missing_packages = _do_latexml(main, outer_bucket_dir, id, False)

            if missing_packages:
                logging.info(f"Missing the following packages: {str(missing_packages)}")
                _insert_missing_package_warning(f'{outer_bucket_dir}/{id}.html', missing_packages)

            # Post process html
            logging.info(f"Step 6: Upload html for {id}")            
            upload_dir_to_gcs(bucket_dir_container, current_app.config['OUT_BUCKET_ARXIV_ID'])
            
            write_success(id, tar_gz, False)
    except:
        logging.info(f'Conversion unsuccessful')
        traceback.print_exc()
        try:
            write_failure(id, tar_gz, False)
        except Exception as e:
            logging.info(f'Failed to write failure for {id} with {e}')
    finally:
        try:
            with id_lock(id, current_app.config['LOCK_DIR'], 1):
                _clean_up(tar_gz, id)
        except Exception as e:
            logging.info(f"Failed to clean up {id} with {e}")
