"""Module that handles the conversion process from LaTeX to HTML"""
import tarfile
import os
import re
import subprocess
import shutil
from typing import Any, Tuple, Dict
import logging
import uuid

from flask import current_app

from ..config import (
    OUT_BUCKET_ARXIV_ID,
    OUT_BUCKET_SUB_ID,
    QA_BUCKET_NAME
)
from ..util import untar, id_lock, timeout
from ..buckets.util import get_google_storage_client
from ..buckets import download_blob, upload_dir_to_gcs, \
    upload_tar_to_gcs
from ..models.db import db
from ..exceptions import *
from .concurrency_control import \
    write_start, write_success, write_failure
from ..addons import inject_addons, copy_static_assets


def process(id: str, blob: str, bucket: str) -> bool:
    is_submission = bucket == current_app.config['IN_BUCKET_SUB_ID']

    """ File system we will be using """
    safe_name = str(uuid.uuid4()) # In case two machines download before locking
    tar_gz = f'{safe_name}.tar.gz' # the file we download the blob to
    src_dir = f'extracted/{id}' # the directory we untar the blob to
    bucket_dir_container = f'{src_dir}/html' # the directory we will upload the *contents* of
    outer_bucket_dir = f'{bucket_dir_container}/{id}' # the highest level directory that will appear in the out bucket
    try:
        os.makedirs(outer_bucket_dir)
    except OSError:
        shutil.rmtree(src_dir)
        os.makedirs(outer_bucket_dir)
        # Abort if this fails
    
    # Check file format and download to ./[{id}.tar.gz]
    logging.info(f"Step 1: Download {id}")
    download_blob(bucket, blob, tar_gz)

    # Write to DB that process has started
    logging.info(f"Write start process to db")
    write_start(id, tar_gz, is_submission)

    try:
        with id_lock(id, current_app.config['LOCK_DIR']):
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
            _do_latexml(main, outer_bucket_dir, id)

            # Post process html
            logging.info(f"Step 6: Upload html for {id}")
            _post_process(bucket_dir_container, id, is_submission)
            
            logging.info(f"Step 7: Upload html for {id}")
            if is_submission:
                upload_tar_to_gcs(id, bucket_dir_container, OUT_BUCKET_SUB_ID, f'{bucket_dir_container}/{id}.tar.gz')
            else:
                upload_dir_to_gcs(bucket_dir_container, OUT_BUCKET_ARXIV_ID)
            
            # TODO: Maybe remove for batch
            download_blob(bucket, blob, tar_gz) # download again to double check for most recent tex source
            write_success(id, tar_gz, is_submission)
    except Exception as e:
        logging.info(f'Conversion unsuccessful with {e}')
        try:
            download_blob(bucket, blob, tar_gz)
            write_failure(id, tar_gz, is_submission)
        except Exception as e:
            logging.info(f'Failed to write failure for {id} with {e}')
    finally:
        try:
            with id_lock(id, current_app.config['LOCK_DIR'], 1):
                _clean_up(tar_gz, id)
        except Exception as e:
            logging.info(f"Failed to clean up {id} with {e}")


def _remove_ltxml(path: str) -> None:
    """
    Remove files with the .ltxml extension from the
    directory "path".

    Parameters
    ----------
    path : str
        File path to the directory containing unzipped .tex source
    """
    try:
        for root, _, files in os.walk(path):
            for file in files:
                if str(file).endswith('.ltxml'):
                    os.remove(os.path.join(root, file))
    except Exception as exc:
        raise LaTeXMLRemoveError(
            f".ltxml file at {path} failed to be removed") from exc


def _find_main_tex_source(path: str) -> str:
    """
    Looks inside the directory at "path" and determines the
    main .tex source. Assumes that the main .tex file
    must start with "documentclass". To account for
    common Overleaf templates that have multiple .tex
    files that start with "documentclass", assumes that
    the main .tex file is not of class "standalone"
    or "subfiles".

    Parameters
    ----------
    path : str
        File path to a directory containing unzipped .tex source

    Returns
    -------
    main_tex_source : str
        File path to the main .tex source in the directory
    """
    try:
        tex_files = [f for f in os.listdir(path) if f.endswith('.tex')]
        if len(tex_files) == 1:
            return os.path.join(path, tex_files[0])
            # Returns the only .tex file in the source files
        else:
            main_files = {}
            for tf in tex_files:
                with open(os.path.join(path, tf), "r") as file:
                    for line in file:
                        if re.search(r"^\s*\\document(?:style|class)", line):
                            # https://arxiv.org/help/faq/mistakes#wrongtex
                            # according to this page, there should only be one tex file with a \documentclass
                            if tf in ["paper.tex", "main.tex", "ms.tex", "article.tex"]:
                                main_files[tf] = 1
                            else:
                                main_files[tf] = 0
                            break
            if len(main_files) == 1:
                return (os.path.join(path, list(main_files)[0]))
            elif len(main_files) == 0:
                raise MainTeXError(
                    f"No main .tex found file in {path}")
            else:
                # account for the two main ways of creating multi-file
                # submissions on overleaf (standalone, subfiles)
                for mf in main_files:
                    with open(os.path.join(path, mf), "r") as file:
                        for line in file:
                            if re.search(r"^\s*\\document(?:style|class).*(?:\{standalone\}|\{subfiles\})", line):
                                main_files[mf] = -99999
                                break
                                # document class of main should not be standalone or subfiles
                                # #the main file is just {article} or something else
                return (os.path.join(path, max(main_files, key=main_files.__getitem__)))
    except Exception as exc:
        raise MainTeXError(
            f"Process to find main .tex file in {path} failed") from exc


def _do_latexml(main_fpath: str, out_dpath: str, sub_id: str) -> None:
    """
    Runs latexml on the .tex file at main_fpath and
    outputs the html at out_fpath.

    Parameters
    ----------
    main_fpath : str
        Main .tex file path
    out_dpath : str
        Output directory file path
    sub_id: str
        submission id of the article
    """
    latexml_config = ["latexmlc",
                      "--preload=[nobibtex,ids,localrawstyles,mathlexemes,magnify=2,zoomout=2,tokenlimit=99999999,iflimit=1499999,absorblimit=1299999,pushbacklimit=599999]latexml.sty",
                      "--path=/opt/arxmliv-bindings/bindings",
                      "--path=/opt/arxmliv-bindings/supported_originals",
                      "--pmml", "--cmml", "--mathtex",
                      "--timeout=2700",
                      "--nodefaultresources",
                      "--css=https://browse.arxiv.org/latexml/ar5iv.min.css",
                      "--graphicimages"
                      f"--source={main_fpath}", f"--dest={out_dpath}/{sub_id}.html"]
    completed_process = subprocess.run(
        latexml_config,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
        text=True,
        timeout=300)
    errpath = os.path.join(os.getcwd(), f"{sub_id}_stdout.txt")
    with open(errpath, "w") as f:
        f.write(completed_process.stdout)
    try:
        bucket = get_google_storage_client().bucket(QA_BUCKET_NAME)
        errblob = bucket.blob(f"{sub_id}_stdout.txt")
        errblob.upload_from_filename(f"{sub_id}_stdout.txt")
    except Exception as exc:
        raise GCPBlobError(
            f"Uploading {sub_id}_stdout.txt to {QA_BUCKET_NAME} failed in do_latexml") from exc
    os.remove(errpath)

def _post_process (src_dir: str, id: str, is_submission: bool):
    """
    Adds the arxiv overlay to the latexml output. This
    includes injecting html and moving static assets

    Parameters
    ----------
    src_dir : str
        path to the directory to be uploaded. This should be 
        in the form of ./extracted/{id}/html/
    bucket_name : str
        submission_id for submissions and paper_id for 
        published documents
    """
    inject_addons(os.path.join(src_dir, f'{id}/{id}.html'), id, is_submission)
    copy_static_assets(os.path.join(src_dir, str(id)))

    
def _clean_up (tar, id):
    os.remove(tar)
    shutil.rmtree(f'extracted/{id}')
