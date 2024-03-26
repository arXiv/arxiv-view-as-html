from typing import Optional
from urllib.parse import urlparse

from flask import current_app
from google.cloud import storage

from arxiv.files.object_store import ObjectStore, LocalObjectStore

from .file_manager import FileManager
from .writable_gs_obj_store import WritableGSObjectStore

_file_manager: Optional[FileManager] = None
_local_conversion_store: Optional[ObjectStore] = None
_local_publish_store: Optional[ObjectStore] = None
_sub_src_store: Optional[ObjectStore] = None
_doc_src_store: Optional[ObjectStore] = None
_sub_converted_store: Optional[ObjectStore] = None
_doc_converted_store: Optional[ObjectStore] = None

def get_global_object_store (path: str, global_name: str) -> ObjectStore:
    """Creates an object store from given path."""
    store = globals().get(global_name)
    if store is None:
        uri = urlparse(path)
        if uri.scheme == "gs":
            gs_client = storage.Client()
            store = WritableGSObjectStore(gs_client.bucket(uri.netloc))
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