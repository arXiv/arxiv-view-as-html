import tarfile
import os
from google.cloud import storage
import logging
import google.cloud.logging
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
    blob.download_to_filename('/source/converted')
    logging.info("get_file")
    # with open(blob_name, 'wb') as read_stream:
    #     blob.download_to_filename(read_stream)
    #     read_stream.close()
    # return os.path.abspath(f"./{blob_name}")
    return '/source/converted'

def untar (fpath):
    with tarfile.open(fpath) as tar:
        #tar.extractall('./static')
        tar.extractall('/source/templates')
        tar.close()
    logging.info("untar")
    list_files("/source/templates")
    return os.path.abspath('/source/templates')
    #return os.path.abspath('./static')