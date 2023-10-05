"""Module that handles the conversion process from LaTeX to HTML"""
import os
import re
import subprocess
import shutil
from typing import (
    Any,
    List, 
    Dict,
    Optional
)
import logging
import traceback
import uuid
from bs4 import BeautifulSoup

from flask import current_app

from ..util import untar, id_lock
from ..buckets.util import get_google_storage_client
from ..buckets import (
    download_blob, 
    upload_dir_to_gcs,
    upload_tar_to_gcs
)
from ..models.db import db
from ..exceptions import *
from .concurrency_control import (
    write_start, 
    write_success, 
    write_failure
)

def process(id: str, blob: str, bucket: str) -> bool:
    is_submission = bucket == current_app.config['IN_BUCKET_SUB_ID']

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
            write_start(id, tar_gz, is_submission)

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
            missing_packages = _do_latexml(main, outer_bucket_dir, id, is_submission)

            if missing_packages:
                logging.info(f"Missing the following packages: {str(missing_packages)}")
                _insert_missing_package_warning(f'{outer_bucket_dir}/{id}.html', missing_packages)
            
            logging.info(f"Step 6: Upload html for {id}")
            if is_submission:
                upload_tar_to_gcs(id, bucket_dir_container, current_app.config['OUT_BUCKET_SUB_ID'], f'{bucket_dir_container}/{id}.tar.gz')
            else:
                # upload_dir_to_gcs(bucket_dir_container, current_app.config['OUT_BUCKET_ARXIV_ID'])
                upload_tar_to_gcs(id, bucket_dir_container, current_app.config['OUT_BUCKET_ARXIV_ID'], f'{bucket_dir_container}/{id}.tar.gz')
            
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
    
def _list_missing_packages (stdout: str) -> Optional[List[str]]:
    MISSING_PACKAGE_RE = re.compile(r"Warning:missing_file:.+Can't\sfind\spackage\s(.+)\sat")
    matches = MISSING_PACKAGE_RE.finditer(stdout)
    return list(map(lambda x: x.group(1), matches)) or None

def _do_latexml(main_fpath: str, out_dpath: str, sub_id: str, is_submission: bool) -> Optional[List[str]]:
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
    LATEXML_URL_BASE = current_app.config['LATEXML_URL_BASE']
    latexml_config = ["latexmlc",
                      "--preload=[nobibtex,ids,localrawstyles,mathlexemes,magnify=2,zoomout=2,tokenlimit=99999999,iflimit=1499999,absorblimit=1299999,pushbacklimit=599999]latexml.sty",
                      "--path=/opt/arxmliv-bindings/bindings",
                      "--path=/opt/arxmliv-bindings/supported_originals",
                      "--pmml", "--cmml", "--mathtex",
                      "--timeout=300",
                      "--nodefaultresources",
                      "--css=https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css",
                      f"--css={LATEXML_URL_BASE}/ar5iv_0.7.4.min.css",
                      f"--css={LATEXML_URL_BASE}/styles.css",
                      "--javascript=https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js",
                      "--javascript=https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.3.3/html2canvas.min.js",
                      f"--javascript={LATEXML_URL_BASE}/addons.js",
                      f"--javascript={LATEXML_URL_BASE}/feedbackOverlay.js",
                      "--navigationtoc=context",
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
        if is_submission:
            bucket = get_google_storage_client().bucket(current_app.config['QA_BUCKET_SUB'])
        else:
            bucket = get_google_storage_client().bucket(current_app.config['QA_BUCKET_DOC'])
        errblob = bucket.blob(f"{sub_id}_stdout.txt")
        errblob.upload_from_filename(f"{sub_id}_stdout.txt")
    except Exception as exc:
        raise GCPBlobError(
            f"Uploading {sub_id}_stdout.txt to {current_app.config['QA_BUCKET_SUB'] if is_submission else current_app.config['QA_BUCKET_DOC']} failed in do_latexml") from exc
    os.remove(errpath)
    return _list_missing_packages(completed_process.stdout)

def _insert_missing_package_warning (fpath: str, missing_packages: List[str]) -> None:
    """ This is the HTML for the closeable pop up warning for missing packages """
    missing_packages_lis = "\n".join(map(lambda x: f"<li>failed: {x}</li>", missing_packages))
    popup_html = f"""
        <div class="package-alerts" role="alert">
            <button aria-label="Dismiss alert" onclick="closePopup()">
                <span aria-hidden="true"><svg role="presentation" width="30" height="30" viewBox="0 0 44 44" aria-hidden="true" focusable="false">
                <path d="M0.549989 4.44999L4.44999 0.549988L43.45 39.55L39.55 43.45L0.549989 4.44999Z" />
                <path d="M39.55 0.549988L43.45 4.44999L4.44999 43.45L0.549988 39.55L39.55 0.549988Z" />
                </svg></span>
            </button>
            <p>HTML conversions sometimes display errors due to content that did not convert correctly from the source. This paper uses the following packages that are not yet supported by the HTML conversion tool. Feedback on these issues are not necessary; they are known and are being worked on.</p>
            <ul>
                {missing_packages_lis}
            </ul>
            <p>Authors: achieve the best HTML results from your LaTeX submissions by selecting from this list of <a href="https://corpora.mathweb.org/corpus/arxmliv/tex_to_html/info/loaded_file" target="_blank">supported packages</a>.</p>
        </div>

        <script>
            function closePopup() {{
                document.querySelector('.package-alerts').style.display = 'none';
            }}
        </script>
    """

    with open(fpath, 'r+') as html:
        soup = BeautifulSoup(html.read(), 'html.parser')
        soup.find('div', attrs={'class': 'ltx_page_content'}).insert(0, BeautifulSoup(popup_html, 'html.parser'))
        html.truncate()
        html.seek(0)
        html.write(str(soup))

def _clean_up (tar, id):
    os.remove(tar)
    shutil.rmtree(f'extracted/{id}')
