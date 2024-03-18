import tarfile

from arxiv.files import UngzippedFileObj, FileObj
from arxiv.files.object_store import ObjectStore, LocalObjectStore
from arxiv.files.key_patterns import (
    abs_path_current_parent, 
    abs_path_orig_parent
)

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
        
        if payload.single_file:
            with src.open('rb') as ungzip_file:
                with open(self.local_store.prefix+src.name, 'xb') as local_file:
                    local_file.write(ungzip_file.read())
            return self.local_store.to_obj(src.name)

        with src.open('rb') as ungzip_file:
            with tarfile.open(fileobj=ungzip_file) as tar:
                tar.extractall(self.local_store.prefix+payload.name)

        main_src = find_main_tex_source(self.local_store.prefix+payload.name)

        return self.local_store.to_obj(main_src)