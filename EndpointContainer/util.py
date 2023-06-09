"""Utility functions for debugging, downloading/untarring files, 
and injecting tags into HTML."""
from typing import Dict
import os
import shutil
import tarfile
import exceptions
from bs4 import BeautifulSoup
from google.cloud import storage
from jinja2 import Template
# import io

def list_files(startpath: str) -> None:
    """
    Lists all the files, directories, and subfiles and subdirectories
    in the directory at startpath

    Parameters
    ----------
    startpath : str
        Directory that we want to walk through
    """
    for root, _, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print(f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print(f'{subindent}{f}/')

def get_file(bucket_name: str, blob_name: str, client: storage.Client) -> str:
    """
    Downloads the .tar.gz file in "blob_name" to "fpath"
    and returns "fpath".

    Parameters
    ----------
    bucket_name : str
        Name of bucket to download from.
    blob_name : str
        Name of blob to download which should be the submission id.
    client : google.cloud.storage.Client
        Google Storage client with access to the desired bucket.
        Created by _get_google_auth()

    Returns
    -------
    fpath : str
        File path to the .tar.gz object that was downloaded
    """
    blob_hyphen = blob_name.replace('.', '-')
    blob_dir = f"/source/templates/{blob_hyphen}/src/"
    try:
        os.makedirs(blob_dir)
    except Exception as exc:
        print(exc)
        print(f"Directory {blob_dir} already exists, remaking directory")
        shutil.rmtree(blob_dir)
        os.makedirs(blob_dir)
    try:
        blob = client.bucket(bucket_name).blob(blob_name)
        blob.download_to_filename(f"/source/templates/{blob_hyphen}/src/{blob_name}")
        return os.path.abspath(f"/source/templates/{blob_hyphen}/src/{blob_name}")
    except Exception as exc:
        raise exceptions.GCPBlobError(f"Download of {blob_name} from {bucket_name} failed") from exc

def get_log(bucket_name: str, blob_name: str, client: storage.Client) -> str:
    """
    Downloads the log .txt file for "blob_name" to "fpath" and returns "fpath".

    Parameters
    ----------
    bucket_name : str
        Name of bucket to download from.
    blob_name : str
        Name of blob to download which should be the submission id.
    client : google.cloud.storage.Client
        Google Storage client with access to the desired bucket.
        Created by _get_google_auth()

    Returns
    -------
    fpath : str
        File path to the .txt object that was downloaded
    """
    blob_name = blob_name + '_stdout.txt'
    blob_dir = "/source/errors/"
    try:
        os.makedirs(blob_dir)
    except Exception as exc:
        print(exc)
        print(f"Directory {blob_dir} already exists, remaking directory")
        shutil.rmtree(blob_dir)
        os.makedirs(blob_dir)
    try:
        blob = client.bucket(bucket_name).blob(blob_name)
        blob.download_to_filename(f"/source/errors/{blob_name}")
        return os.path.abspath(f"/source/errors/{blob_name}")
    except Exception as exc:
        print(exc)
        raise exceptions.GCPBlobError(f"Download of {blob_name} from {bucket_name} failed") from exc

def untar(fpath: str, id: str) -> str:
    """
    Extracts the .tar.gz at "fpath" into directory
    "/source/templates/{id_hyphen}".

    Parameters
    ----------
    fpath : str
        File path to the .tar.gz object
    id : str
        Name that we want to give to the directory
        that contains the extracted files

    Returns
    -------
    htmlpath : str
        File path of the extracted html without
        "/source/templates" prepended to it.
    """
    try:
        id_hyphen = id.replace(".", "-")
        with tarfile.open(fpath) as tar:
            tar.extractall(f'/source/templates/{id_hyphen}')
            tar.close()
        return f'{id_hyphen}/{id}.html'
    except Exception as exc:
        raise exceptions.TarError(f"Tarfile at {fpath} failed to extract in untar()") from exc

def _inject_html_addon (soup: BeautifulSoup, parent_tag: str, position: int, payload_fpath: str, **template_args: Dict[str, str]) -> BeautifulSoup:
    """
    Injects arbitrary html into the given parent tag in the src
    html file. The payload is placed inside the provided parent tag
    at the given position

    Parameters
    ----------
    src_fpath : String
        File path to the html files, relative to the
        /source/templates dir, where all the html 
        should live
    payload_fpath : String
        The path to the html to be injected
    parent_tag: str
        The tag of the parent element. Usually 'head' or 'body'
    position : int
        The numerical index of the position of the element in the subtree of the parent_tag
    """
    try:
        with open(f'/source/addons/{payload_fpath}', 'r') as payload:
            template = Template(payload.read())
            block = BeautifulSoup(template.render(**template_args), 'html.parser')
            soup.find(parent_tag).insert(position, block)
            return soup
    except Exception as exc:
        raise exceptions.HTMLInjectionError(f"Failed to inject {payload_fpath} with {exc}") from exc
      

def inject_addons (src_fpath: str, identifier: str):
    
    with open(f'/source/templates/{src_fpath}', 'r+') as source:
        soup = BeautifulSoup(source.read(), 'html.parser')
        # Inject base tag into head
        soup = _inject_html_addon(soup, 'head', 6, 'base.html', base_path=identifier.replace('.', '-'))
        # Inject header block into body
        soup = _inject_html_addon(soup, 'body', 1, 'header.html')
        # Inject body message into body
        soup = _inject_html_addon(soup, 'body', 2, 'body_message.html')
        # Inject style block into head
        soup = _inject_html_addon(soup, 'head', 7, 'style.html')

        # Add id="main" to <div class="ltx_page_main">
        soup.find('div', {'class': 'ltx_page_main'})['id'] = 'main'
        
        # Overwrite original file with the new addons
        source.seek(0)
        source.write(str(soup))
    

