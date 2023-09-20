import os
import tarfile

from google.cloud import storage
from flask import current_app

from ..buckets import download_blob, \
    upload_dir_to_gcs, delete_blob
from ..util import untar
from .util import rename

storage_client = storage.Client()

def move_sub_to_doc_bucket (submission_id: int, paper_idv: str):
    blob_name = f'{submission_id}.tar.gz'
    tar_name = f'{submission_id}.tar'
    dir_name = f'sites/{submission_id}'
    download_blob(current_app.config['OUT_BUCKET_SUB_ID'], blob_name, tar_name)
    untar(tar_name, dir_name)
    rename(dir_name, submission_id, paper_idv)
    upload_dir_to_gcs(dir_name, current_app.config['OUT_BUCKET_ARXIV_ID'])

def move_sub_qa_to_doc_qa (submission_id: str, paper_idv: str):
    blob_name = f'{submission_id}_stdout.txt'
    out_name = f'{paper_idv}_stdout.txt'
    bucket = storage_client.bucket(current_app.config['QA_BUCKET_SUB'])
    bucket.copy_blob(
        bucket.blob(blob_name), 
        storage_client.bucket(current_app.config['QA_BUCKET_DOC']), 
        out_name)

def delete_sub (submission_id: int):
    delete_blob (current_app.config['OUT_BUCKET_SUB_ID'], f'{submission_id}.tar.gz')

