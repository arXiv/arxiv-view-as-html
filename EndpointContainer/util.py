import tarfile
import os
from google.cloud import storage
import logging
import google.cloud.logging
import io
import jinja2
import shutil
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
