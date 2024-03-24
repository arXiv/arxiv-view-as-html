import os
from urllib.parse import urlparse

from flask import current_app
from google.cloud import storage

from arxiv.files import FileObj, LocalFileObj
from arxiv.files.object_store import ObjectStore, \
    GsObjectStore, LocalObjectStore

from .file_manager import FileManager

_file_manager: FileManager = None
_local_conversion_store = None
_local_publish_store = None
_sub_src_store = None
_doc_src_store = None
_sub_converted_store = None
_doc_converted_store = None

class WritableGsObjectStore (GsObjectStore):

    def write_obj (self, obj_in: FileObj, obj_out: FileObj, **kwargs):
        if obj_out.exists():
            obj_out.delete()
        with obj_in.open('rb') as f_in:
            with obj_out.open('wb') as f_out:
                f_out.write(f_in.read())

    def copy_local_dir (self, path_in: str, path_out: str):
        for root, _, fnames in os.walk(path_in):
            for fname in fnames:
                abs_fpath = os.path.join(root, fname)
                obj_in = LocalFileObj(abs_fpath)
                obj_out = self.bucket.blob(
                    os.path.join(
                        path_out,
                        os.path.relpath(
                            abs_fpath,
                            path_in
                        )
                    )
                )
                self.write_obj(obj_in, obj_out)

def get_global_object_store (path: str, global_name: str) -> ObjectStore:
    """Creates an object store from given path."""
    store = globals().get(global_name)
    if store is None:
        uri = urlparse(path)
        if uri.scheme == "gs":
            gs_client = storage.Client()
            store = WritableGsObjectStore(gs_client.bucket(uri.netloc))
        else:
            store = LocalObjectStore(path)
        globals()[global_name] = store
    return store

def get_file_manager () -> "FileManager":
    global _file_manager
    if _file_manager is None:
        config= current_app.config
        _file_manager = FileManager(
            sub_src_store=get_global_object_store(config['SUBMISSION_SOURCE_BUCKET'], '_sub_src_store'),
            doc_src_store=get_global_object_store(config['DOCUMENT_SOURCE_BUCKET'], '_doc_src_store'),
            local_conversion_store=get_global_object_store(config['LOCAL_CONVERSION_DIR'], '_local_conversion_store'),
            local_publish_store=get_global_object_store(config['LOCAL_PUBLISH_DIR'], '_local_publish_store'),
            sub_converted_store=get_global_object_store(config['SUBMISSION_CONVERTED_BUCKET'], '_sub_converted_store'),
            doc_converted_store=get_global_object_store(config['DOCUMENT_CONVERTED_BUCKET'], '_doc_converted_store'),
        )
    return _file_manager