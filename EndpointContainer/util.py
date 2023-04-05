import tarfile
import os
from google.cloud import storage
import logging
import google.cloud.logging
import io
import jinja2
import shutil
from bs4 import BeautifulSoup

client = google.cloud.logging.Client()
client.setup_logging()

def list_files(startpath):
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        logging.info('{}{}/'.format(indent, os.path.basename(root)))
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            logging.info('{}{}'.format(subindent, f))

def get_file(bucket_name, blob_name, client):
    """
    Downloads the .tar.gz file in "blob_name" to "fpath".

    Parameters
    ----------
    bucket_name : String
        Name of bucket to download from.
    blob_name : String
        Name of blob to download which should be the submission id.
    client : google.cloud.storage.Client
        Google Storage client with access to the desired bucket.
        Create by _get_google_auth()

    Returns
    -------
    fpath : String
        File path to the .tar.gz object that was downloaded
    """
    blob = client.bucket(bucket_name) \
        .blob(blob_name)
    
    blob_hyphen = blob_name.replace('.', '-')
    blob_dir = f"/source/templates/{blob_hyphen}/src/"
    try:
        os.makedirs(blob_dir)
    except:
        logging.info(f"Directory {blob_dir} already exists, remaking directory")
        shutil.rmtree(blob_dir)
        os.makedirs(blob_dir)

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

def untar (fpath, id):
    """
    Extracts the .tar.gz at "fpath" into directory
    "/source/templates/{id_hyphen}".

    Parameters
    ----------
    fpath : String
        File path to the .tar.gz object
    id : String
        Name that we want to give to the directory
        that contains the extracted files

    Returns
    -------
    htmlpath : String
        File path of the extracted html without
        "/source/templates" prepended to it.
    """
    id_hyphen = id.replace(".", "-")
    with tarfile.open(fpath) as tar:
        tar.extractall(f'/source/templates/{id_hyphen}')
        tar.close()
    return f'{id_hyphen}/html/{id}.html'

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
    _inject_into_head(html_path, 'base', { 'href' : base_path })

def _inject_into_head (html_path: str, tag: str, attribs: dict) -> None:
    
    try:
        with open(f'/source/templates/{html_path}', 'r+') as html:
            soup = BeautifulSoup(html.read(), 'html.parser')
            new_tag = soup.new_tag(tag)
            for k, v in attribs:
                new_tag[k] = v
            soup.find('head').append(new_tag)
            html.seek(0)
            html.write(str(soup))
    except Exception as e:
        print (f'Failed to inject {tag} into head of {html_path} with {e}')
        raise

def _inject_into_body (html_path: str, tag: str, attribs: dict) -> None:
    try:
        with open(f'/source/templates/{html_path}', 'r+') as html:
            soup = BeautifulSoup(html.read(), 'html.parser')
            new_tag = soup.new_tag(tag)
            for k, v in attribs:
                new_tag[k] = v
            soup.find('body').append(new_tag)
            html.seek(0)
            html.write(str(soup))
    except Exception as e:
        print (f'Failed to inject {tag} into body of {html_path} with {e}')
        raise