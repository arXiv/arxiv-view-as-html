import tarfile
import os
import logging

from arxiv.files import UngzippedFileObj, FileObj
from arxiv.files.object_store import ObjectStore, LocalObjectStore
from arxiv.files.key_patterns import (
    abs_path_current_parent, 
    abs_path_orig_parent
)

from google.cloud import storage
from flask import current_app

from ...domain.conversion import ConversionPayload, \
    SubmissionConversionPayload, DocumentConversionPayload
from .main_src import find_main_tex_source

def sub_src_path (payload: SubmissionConversionPayload) -> str:
    src_ext = '.gz' if payload.single_file else '.tar.gz'
    return f'{payload.identifier}/{payload.identifier}{src_ext}'

def doc_src_path (payload: DocumentConversionPayload) -> str:
    src_ext = '.gz' if payload.single_file else '.tar.gz'
    path = abs_path_current_parent(payload.identifier) if payload.is_latest \
        else abs_path_orig_parent(payload.identifier)
    return f'{path}/{payload.identifier.filename}{src_ext}'    

class FileManager:

    def __init__ (self, 
                  sub_src_store: ObjectStore, 
                  doc_src_store: ObjectStore,
                  local_store: LocalObjectStore):
        self.sub_src_store = sub_src_store
        self.doc_src_store = doc_src_store
        self.local_store = local_store

    def download_source (self, payload: ConversionPayload) -> FileObj:
        """
        Download the src files and return the main tex file
        """

        if isinstance(payload, DocumentConversionPayload):
            src = UngzippedFileObj(self.doc_src_store.to_obj(doc_src_path(payload)))
        else:
            src = UngzippedFileObj(self.sub_src_store.to_obj(sub_src_path(payload)))
            logging.info(f'SRC STORE: {self.sub_src_store}')
            logging.info(f'SRC: {src}')
        
        
        if payload.single_file:
            with src.open('rb') as ungzip_file:
                with open(f'{self.local_store.prefix}{payload.name}/{src.name}', 'wb+') as local_file:
                    local_file.write(ungzip_file.read())
            return self.local_store.to_obj(f'{payload.name}/{src.name}')

        with src.open('rb') as ungzip_file:
            with tarfile.open(fileobj=ungzip_file) as tar:
                tar.extractall(self.local_store.prefix+payload.name)

        main_src = find_main_tex_source(self.local_store.prefix+payload.name)

        return self.local_store.to_obj(os.path.relpath(main_src, self.local_store.prefix))
    
    def latexml_output_dir (self, payload: ConversionPayload) -> str:
        return f'{self.local_store.prefix}{payload.name}/html/{payload.name}/'
    
    def upload_dir (self, payload: ConversionPayload) -> str:
        return f'{self.local_store.prefix}{payload.name}/html/'
    
    def upload_latexml (self, payload: ConversionPayload, metadata: str):
        src_dir = self.upload_dir(payload)
        with open(f'{self.latexml_output_dir(payload)}{payload.name}_metadata.json', 'w+') as meta:
            meta.write(metadata)

        if isinstance(payload, DocumentConversionPayload):
            bucket = storage.Client().bucket(current_app.config['DOCUMENT_CONVERTED_BUCKET'])
            for root, _, fnames in os.walk(src_dir):
                for fname in fnames:
                    abs_fpath = os.path.join(root, fname)
                    bucket.blob(
                        os.path.relpath(
                            abs_fpath,
                            src_dir
                        )
                    ) \
                    .upload_from_filename(abs_fpath)
        else:
            destination_fname = f'{src_dir}{payload.name}.tar.gz'
            bucket = storage.Client().bucket(current_app.config['SUBMISSION_CONVERTED_BUCKET'])
            with tarfile.open(destination_fname, "w:gz") as tar:
                tar.add(f'{src_dir}/{payload.name}', arcname=str(payload.name))
            blob = bucket.blob(f'{payload.name}.tar.gz')
            blob.upload_from_filename(destination_fname)
