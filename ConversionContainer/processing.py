"""Module that handles the conversion process from LaTeX to HTML"""
import tarfile
import os
import re
import subprocess
import shutil
from typing import Any, Union, Optional, AnyStr
import config
from models.db import db
import exceptions
from google.cloud import storage
from concurrency_control import write_start, write_success

# Change such that we can handle multiple requests
# Raise max requests allowed on cloud run
# Error handling try/catch - send event maybe

client = storage.Client()


def process(payload: dict[str, Any]) -> bool:
    """
    Runs latexml on the blob in the payload and uploads
    the results to the output bucket in the config
    file.

    Parameters
    ----------
    payload : JSON
        https://github.com/googleapis/google-cloudevents/blob/main/proto/google/events/cloud/storage/v1/data.proto

    Returns
    -------
    Boolean
        Returns true unless an exception occurs

    Raises
    ------
    Exception
        'PayloadError': No submission id (payload.name)
            contained in the payload. Likely the entire
            payload is invalid/malformed.
    """
    try:
        payload_name = payload['name']
        out_path = None
        # Looking for subid/subid.tar.gz
        if payload_name:
            # db.write_in_progress(payload_name)
            pass
        else:
            raise exceptions.PayloadError('No submission_id')
        print("Step 1: downloading")
        tar, id = get_file(payload)
        write_start(int(id), tar)
        print(f"Step 2: untarring {tar}")
        source = untar(tar, id)
        print("Step 3: Removing .ltxml files")
        remove_ltxml(source)
        print("Step 4: finding main tex source")
        main = find_main_tex_source(source)
        print(f"Main tex source is {main}")
        out_path = os.path.join(source, 'html')
        try:
            os.mkdir(out_path)
        except FileExistsError:
            for filename in os.listdir(out_path):
                filepath = os.path.join(out_path, filename)
                try:
                    shutil.rmtree(filepath)
                except OSError:
                    os.remove(filepath)
        print(f"Out path is {out_path}")
        print("Step 5: Do LaTeXML")
        do_latexml(main, os.path.join(out_path, id), id)
        print(f"Step 6: Upload html from {out_path}, {payload['bucket']}")
        if payload['bucket'] == config.IN_BUCKET_ARXIV_ID:
            upload_output(out_path, config.OUT_BUCKET_ARXIV_ID, id)
        else:
            tar, id = get_file(payload)
            if write_success(int(id), tar):
                upload_output(out_path, config.OUT_BUCKET_SUB_ID, id)
        print("Uploaded successfully. Done!")
        
        # db.write_success(payload_name)
    except Exception as e:
        print(e)
        # if payload.get('name'):
        #     db.write_failure(payload['name'])
        # else:
        #     pass
            # what to do if we got a bad submission_id?
    finally:
        if out_path:
            try:
                shutil.rmtree(out_path)
            except Exception as e:
                print(e)
                print(f"Failed to delete {out_path}")
    return True


def get_file(payload: dict[str, Any]) -> tuple[str, str]:
    """
    Checks if the payload contains a .tar.gz file
    and if so it downloads the file to "fpath".
    Otherwise, it throws an Exception, ending the process
    and logging the non .tar.gz file.

    Parameters
    ----------
    payload : dict[str, Any]
        https://github.com/googleapis/google-cloudevents/blob/main/proto/google/events/cloud/storage/v1/data.proto

    Returns
    -------
    fpath : str
        File path to the .tar.gz object
    """
    if payload['name'].endswith('.gz'):
        fname = payload['name'].split('/')[1]
        id = fname.split('.')[0]
        try:
            os.remove(f"./{fname}")
        except:
            pass
    else:
        raise exceptions.FileTypeError(f"{payload['name']} was not a .tar.gz")
    try:
        blob = client.bucket(payload['bucket']) \
            .blob(payload['name'])
        with open(fname, 'wb') as read_stream:
            blob.download_to_file(read_stream)
            read_stream.close()
        return os.path.abspath(f"./{fname}"), id
    except Exception as exc:
        raise exceptions.GCPBlobError(
            f"Download of {payload['name']} from {payload['bucket']} failed") from exc


def untar(fpath: str, dir_name: str) -> str:
    """
    Extracts the .tar.gz at "fpath" into directory
    "dir_name".

    Parameters
    ----------
    fpath : str
        File path to the .tar.gz object
    dir_name : str
        Name that we want to give to the directory
        that contains the extracted files

    Returns
    -------
    extracted_directory : str
        File path of the directory that contains the
        extracted files
    """
    try:
        with tarfile.open(fpath) as tar:
            # Assuming they protect us from files with ../ or / in the name
            tar.extractall(f"extracted/{dir_name}")
            tar.close()
        return os.path.abspath(f"extracted/{dir_name}")
    except Exception as exc:
        raise exceptions.TarError(
            f"Tarfile at {fpath} failed to extract in untar()") from exc


def remove_ltxml(path: str) -> None:
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
        raise exceptions.LaTeXMLRemoveError(
            f".ltxml file at {path} failed to be removed") from exc


def find_main_tex_source(path: str) -> str:
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
                raise exceptions.MainTeXError(
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
        raise exceptions.MainTeXError(
            f"Process to find main .tex file in {path} failed") from exc


def do_latexml(main_fpath: str, out_dpath: str, sub_id: str) -> None:
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
                      "--css=css/ar5iv.min.css",
                      f"--source={main_fpath}", f"--dest={out_dpath}.html"]
    completed_process = subprocess.run(
        latexml_config,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
        text=True)
    errpath = os.path.join(os.getcwd(), f"{sub_id}_stdout.txt")
    with open(errpath, "w") as f:
        f.write(completed_process.stdout)
    try:
        bucket = client.bucket(config.QA_BUCKET_NAME)
        errblob = bucket.blob(f"{sub_id}_stdout.txt")
        errblob.upload_from_filename(f"{sub_id}_stdout.txt")
    except Exception as exc:
        raise exceptions.GCPBlobError(
            f"Uploading {sub_id}_stdout.txt to {config.QA_BUCKET_NAME} failed in do_latexml") from exc
    os.remove(errpath)


def upload_output(path: str, bucket_name: str, destination_fname: str) -> None:
    """
    Uploads a .tar.gz object named {destination_fname}
    containing a folder called "html" located at {path}
    to the bucket named {bucket_name}. 

    Parameters
    ----------
    path : str
        Directory path in format /.../.../sub_id/html
        containing the static files for ar        # Read and update hash in chunks of 4K
the object to.
    destination_fname : str
        What to name the .tar.gz object, should be the
        submission id.
    """
    try:
        destination_fpath = os.path.join(os.getcwd(), destination_fname)
        with tarfile.open(destination_fpath, "w:gz") as tar:
            tar.add(path, arcname=os.path.basename(path))
        with open(destination_fpath, 'r') as temp:
            temp.seek(0, os.SEEK_END)
            print(f"Tar size: {temp.tell()}")
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_fname)
        print(f"Blob info: {blob.name}")
        blob.upload_from_filename(destination_fpath)
    except Exception as exc:
        print(exc)
        raise exceptions.GCPBlobError(
            f"Upload of {destination_fname} to {bucket_name} failed") from exc
    finally:
        try:
            os.remove(destination_fpath)
        except Exception as exc:
            print(exc)
            raise exceptions.CleanupError(
                f"Failed to remove {destination_fpath} in upload_output()") from exc
