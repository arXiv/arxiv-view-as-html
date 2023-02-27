import tarfile
import os
from google.cloud import storage
import logging
import google.cloud.logging
import io
import jinja2
client = google.cloud.logging.Client()
client.setup_logging()

OUT_BUCKET_NAME = "latexml_submission_converted"

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
    try:
        os.makedirs(f"/source/templates/{blob_name}/src/")
    except:
        logging.info(f"Directory /source/templates/{blob_name}/src/ already exists")
    blob.download_to_filename(f"/source/templates/{blob_name}/src/{blob_name}")
    logging.info("get_file")
    # file_obj = io.BytesIO()
    # # with open(blob_name, 'wb') as read_stream:
    # #     blob.download_to_filename(read_stream)
    # #     read_stream.close()
    # blob.download_to_filename(file_obj)
    # file_obj.seek(0, 0)
    # with open(blob_name, 'wb') as f:
    #     f.write(file_obj.getbuffer())
    return os.path.abspath(f"/source/templates/{blob_name}/src/{blob_name}")
    # return '/source/converted'

def untar (fpath, id):
    with tarfile.open(fpath) as tar:
        #tar.extractall('./static')
        tar.extractall(f'/source/templates/{id}')
        tar.close()
    logging.info("untar")
    list_files(f"/source/templates/{id}")
    return f'{id}/html/{id}.html'
    #return os.path.abspath('./static')