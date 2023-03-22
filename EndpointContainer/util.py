import tarfile
import os
from google.cloud import storage
import logging
import google.cloud.logging
import io
import jinja2
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
    blob = client.bucket(bucket_name) \
        .blob(blob_name)
    
    blob_hyphen = blob_name.replace('.', '-')
    try:
        os.makedirs(f"/source/templates/{blob_hyphen}/src/")
    except:
        logging.info(f"Directory /source/templates/{blob_hyphen}/src/ already exists")

    blob.download_to_filename(f"/source/templates/{blob_hyphen}/src/{blob_name}")
    logging.info("get_file")
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
    id_hyphen = id.replace(".", "-")
    with tarfile.open(fpath) as tar:
        tar.extractall(f'/source/templates/{id_hyphen}')
        tar.close()
    return f'{id_hyphen}/html/{id}.html'
    #return os.path.abspath('./static')
