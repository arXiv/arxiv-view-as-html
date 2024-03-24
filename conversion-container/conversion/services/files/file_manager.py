from typing import Tuple
from io import BytesIO
import tarfile
import os
import shutil
import hashlib

from arxiv.files import UngzippedFileObj, FileObj
from arxiv.files.object_store import ObjectStore, LocalObjectStore
from arxiv.files.key_patterns import (
    abs_path_current_parent, 
    abs_path_orig_parent
)

from google.cloud import storage
from flask import current_app

from ...domain.conversion import (
    ConversionPayload,
    SubmissionConversionPayload, 
    DocumentConversionPayload,
    LaTeXMLOutput
)
from ...domain.publish import PublishPayload
from ..latexml.metadata import generate_metadata
from .main_src import find_main_tex_source
from . import WritableGsObjectStore

def sub_src_path (payload: SubmissionConversionPayload) -> str:
    src_ext = '.gz' if payload.single_file else '.tar.gz'
    return f'{payload.identifier}/{payload.identifier}{src_ext}'

def doc_src_path (payload: DocumentConversionPayload) -> str:
    src_ext = '.gz' if payload.single_file else '.tar.gz'
    path = abs_path_current_parent(payload.identifier) if payload.is_latest \
        else abs_path_orig_parent(payload.identifier)
    return f'{path}/{payload.identifier.filename}{src_ext}'

def _get_checksum (input_bytes: bytes) -> str:
    return hashlib.md5(input_bytes).hexdigest()

class FileManager:

    def __init__ (self, 
                  sub_src_store: ObjectStore, 
                  doc_src_store: ObjectStore,
                  local_conversion_store: LocalObjectStore,
                  local_publish_store: LocalObjectStore,
                  sub_converted_store: WritableGsObjectStore,
                  doc_converted_store: WritableGsObjectStore):
        self.sub_src_store = sub_src_store
        self.doc_src_store = doc_src_store
        self.local_conversion_store = local_conversion_store
        self.local_publish_store = local_publish_store
        self.sub_converted_store = sub_converted_store
        self.doc_converted_store = doc_converted_store

    def download_source (self, payload: ConversionPayload) -> Tuple[str, FileObj]:
        """
        Download the src files and return the main tex file
        """

        if isinstance(payload, DocumentConversionPayload):
            src = UngzippedFileObj(self.doc_src_store.to_obj(doc_src_path(payload)))
        else:
            src = UngzippedFileObj(self.sub_src_store.to_obj(sub_src_path(payload)))

        with src.open('rb') as ungzip_file:
            input_bytes = ungzip_file.read()
            checksum = _get_checksum(input_bytes)
        
        if payload.single_file:
            with open(f'{self.local_conversion_store.prefix}{payload.name}/{src.name}', 'wb+') as local_file:
                input_bytes = ungzip_file.read()
                checksum = _get_checksum(input_bytes)
                local_file.write(input_bytes)
            return checksum, self.local_conversion_store.to_obj(f'{payload.name}/{src.name}')

        with tarfile.open(fileobj=BytesIO(input_bytes)) as tar:
            tar.extractall(self.local_conversion_store.prefix+payload.name)

        main_src = find_main_tex_source(self.local_conversion_store.prefix+payload.name)

        return checksum, self.local_conversion_store.to_obj(os.path.relpath(main_src, self.local_conversion_store.prefix))
    
    def _latexml_output_dir_name (self, payload: ConversionPayload) -> str:
        return f'{self.local_conversion_store.prefix}{payload.name}/html/{payload.name}/'
    
    def _upload_dir_name (self, payload: ConversionPayload) -> str:
        return f'{self.local_conversion_store.prefix}{payload.name}/html/'
    
    def write_latexml_extras (self, payload: ConversionPayload, latexml_output: LaTeXMLOutput):
        metadata = generate_metadata(payload, latexml_output.missing_packages)
        with open(f'{self._latexml_output_dir_name(payload)}__metadata.json', 'w') as f:
            f.write(metadata)
        with open(f'{self._latexml_output_dir_name(payload)}__stdout.txt', 'w') as f:
            f.write(latexml_output.output)
    
    def upload_latexml (self, payload: ConversionPayload):
        """
        Upload the latexml and metadata for the given payload. Delete the 
        working directory for the payload after.
        """
        src_dir = self._upload_dir_name(payload)
        if isinstance(payload, DocumentConversionPayload):
            self.doc_converted_store.copy_local_dir(self.local_publish_store.prefix+payload.paper_id.idv, '')
        else:
            destination_fname = f'{src_dir}{payload.name}.tar.gz'
            bucket = storage.Client().bucket(current_app.config['SUBMISSION_CONVERTED_BUCKET'])
            with tarfile.open(destination_fname, "w:gz") as tar:
                tar.add(f'{src_dir}/{payload.name}', arcname=str(payload.name))
            blob = bucket.blob(f'{payload.name}.tar.gz')
            blob.upload_from_filename(destination_fname)
        
        self.clean_up(payload)

    
    def remove_ltxml(self, payload: ConversionPayload) -> None:
        """
        Remove files with the .ltxml extension from the working
        directory of the payload
        """
        for root, _, files in os.walk(self.local_conversion_store.prefix+payload.name):
            for file in files:
                if str(file).endswith('.ltxml'):
                    os.remove(os.path.join(root, file))

    
    def clean_up (self, payload: ConversionPayload):
        shutil.rmtree(self.local_conversion_store.prefix+payload.name)

    
    def download_submission_conversion (self, payload: PublishPayload) -> None:
        # Download and expand submission conversion .tar.gz
        sub_conversion = UngzippedFileObj(
            self.sub_converted_store.to_obj(f'{payload.submission_id}.tar.gz'))
        with sub_conversion.open('rb') as ungzip_file:
            with tarfile.open(fileobj=ungzip_file) as tar:
                tar.extractall(self.local_publish_store.prefix)

        # Rename outer directory and html file to paper_idv
        os.rename(
            f'{self.local_publish_store.prefix}{payload.submission_id}',
            f'{self.local_publish_store.prefix}{payload.paper_id.idv}',
        )
        os.rename(
            f'{self.local_publish_store.prefix}{payload.paper_id.idv}/{payload.submission_id}.html',
            f'{self.local_publish_store.prefix}{payload.paper_id.idv}/{payload.paper_id.idv}.html'
        )

    # TODO: refactor so publish and convert can use
    def upload_document_conversion (self, payload: PublishPayload) -> None:
        # Upload directory back
        self.doc_converted_store.copy_local_dir(self.local_publish_store.prefix+payload.paper_id.idv,
                                                payload.paper_id.idv)

