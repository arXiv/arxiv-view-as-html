from flask import current_app
from urllib.parse import urlparse
from google.cloud import storage

from arxiv.files.object_store import ObjectStore, \
    GsObjectStore, LocalObjectStore

from .file_manager import FileManager

_file_manager: FileManager = None
_local_store = None
_sub_src_store = None
_doc_src_store = None

def get_global_object_store (path: str, global_name: str) -> ObjectStore:
    """Creates an object store from given path."""
    store = globals().get(global_name)
    if store is None:
        uri = urlparse(path)
        if uri.scheme == "gs":
            gs_client = storage.Client()
            store = GsObjectStore(gs_client.bucket(uri.netloc))
        else:
            store = LocalObjectStore(path)
        globals()[global_name] = store
    return store

def get_file_manager () -> "FileManager":
    global _file_manager
    if _file_manager is None:
        config= current_app.config
        _file_manager = FileManager(
            sub_src_store=get_global_object_store(config['SUBMISSION_SOURCE_BUCKET'], _sub_src_store),
            doc_src_store=get_global_object_store(config['DOCUMENT_SOURCE_BUCKET'], _doc_src_store),
            local_store=get_global_object_store(config['LOCAL_WORK_DIR'], _local_store)
        )