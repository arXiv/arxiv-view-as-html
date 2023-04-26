"""Utility functions for debugging, downloading/untarring files, 
and injecting tags into HTML."""
import os
import shutil
import tarfile
import exceptions
from bs4 import BeautifulSoup
from google.cloud import storage
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
        blob = client.bucket(bucket_name) \
            .blob(blob_name)
        blob.download_to_filename(f"/source/templates/{blob_hyphen}/src/{blob_name}")
        # file_obj = io.BytesIO()
        # # with open(blob_name, 'wb') as read_stream:
        # #     blob.download_to_filename(read_stream)
        # #     read_stream.close()
        # blob.download_to_filename(file_obj)
        # file_obj.seek(0, 0)
        # with open(blob_name, 'wb') as f:
        #     f.write(file_obj.getbuffer())
        return os.path.abspath(f"/source/templates/{blob_hyphen}/src/{blob_name}")
    except Exception as exc:
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
        return f'{id_hyphen}/html/{id}.html'
    except Exception as exc:
        raise exceptions.TarError(f"Tarfile at {fpath} failed to extract in untar()") from exc

def inject_base_tag (html_path: str, base_path: str) -> None:
    """
    Appends a <base> html tag to the end of the head 
    section of a given html file

    Parameters
    ----------
    html_path : String
        File path to the html files, relative to the
        /source/templates dir, where all the html 
        should live
    base_path : String
        The value that should be assigned to the href
        attribute of the <base> element. Like...
        <base href=[base_path]>

    Returns
    -------
    None
    """
    try:
        _inject_into_head(html_path, 'base', { 'href' : base_path })
    except Exception as exc:
        raise exceptions.HTMLInjectionError(f"Failed to append values at \
            {base_path} into html at {html_path}") from exc

def _inject_into_head (html_path: str, tag: str, attribs: dict) -> None:
    """
    Injects a tag into the "head" element of the HTML file with
    attributes 'attribs'. Tag is placed at the end of the "head"
    element after all existing tags.

    Parameters
    ----------
    html_path : String
        File path to the html files, relative to the
        /source/templates dir, where all the html 
        should live
    tag : String
        A valid BeautifulSoup tag
        https://www.crummy.com/software/BeautifulSoup/bs4/doc/#bs4.Tag
    attribs : dict
        Valid BeautifulSoup tag "attrs"
        https://www.crummy.com/software/BeautifulSoup/bs4/doc/#bs4.Tag
    """
    try:
        with open(f'/source/templates/{html_path}', 'r+') as html:
            soup = BeautifulSoup(html.read(), 'html.parser')
            new_tag = soup.new_tag(tag)
            for k, v in attribs.items():
                new_tag[k] = v
            soup.find('head').append(new_tag)
            html.seek(0)
            html.write(str(soup))
    except Exception as exc:
        raise exceptions.HTMLInjectionError(f"Failed to inject {tag} into \
            head of {html_path} with {exc}") from exc

def _inject_into_body (html_path: str, tag: str, attribs: dict) -> None:
    """Injects a tag into the "body" element of the HTML file with
    attributes 'attribs'. Tag is placed at the end of the "body"
    element after all existing tags.

    Parameters
    ----------
    html_path : String
        File path to the html files, relative to the
        /source/templates dir, where all the html 
        should live
    tag : String
        A valid BeautifulSoup tag
        https://www.crummy.com/software/BeautifulSoup/bs4/doc/#bs4.Tag
    attribs : dict
        Valid BeautifulSoup tag "attrs"
        https://www.crummy.com/software/BeautifulSoup/bs4/doc/#bs4.Tag
    """
    try:
        with open(f'/source/templates/{html_path}', 'r+') as html:
            soup = BeautifulSoup(html.read(), 'html.parser')
            new_tag = soup.new_tag(tag)
            for k, v in attribs:
                new_tag[k] = v
            soup.find('body').append(new_tag)
            html.seek(0)
            html.write(str(soup))
    except Exception as exc:
        raise exceptions.HTMLInjectionError(f"Failed to inject {tag} into \
            body of {html_path} with {exc}") from exc
