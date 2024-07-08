from typing import Tuple
from io import BytesIO
import tarfile
import os
import shutil
import hashlib
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_fixed

from arxiv.files import UngzippedFileObj, FileObj, LocalFileObj
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
)
from ...domain.publish import PublishPayload
from .main_src import find_main_tex_source
from .writable_obj_store import WritableObjectStore
from tex_inspection import find_primary_tex, ZeroZeroReadMe

def sub_src_path (payload: SubmissionConversionPayload) -> str:
    src_ext = '.gz' if payload.single_file else '.tar.gz'
    return f'{payload.identifier}/{payload.identifier}{src_ext}'

def doc_src_path (payload: DocumentConversionPayload) -> str:
    src_ext = '.gz' if payload.single_file else '.tar.gz'
    path = abs_path_current_parent(payload.identifier) if payload.is_latest \
        else abs_path_orig_parent(payload.identifier)
    fname = f'{payload.identifier.filename}{"" if payload.is_latest else ("v" + str(payload.identifier.version))}'
    print (f'{path}/{fname}{src_ext}')
    return f'{path}/{fname}{src_ext}'

def _get_checksum (input_bytes: bytes) -> str:
    return hashlib.md5(input_bytes).hexdigest()

class FileManager:

    def __init__ (self, 
                  sub_src_store: ObjectStore, 
                  doc_src_store: ObjectStore,
                  local_conversion_store: ObjectStore,
                  local_publish_store: ObjectStore,
                  sub_converted_store: ObjectStore,
                  doc_converted_store: ObjectStore):
        self.sub_src_store = sub_src_store
        self.doc_src_store = doc_src_store

        assert isinstance(local_conversion_store, LocalObjectStore)
        self.local_conversion_store = local_conversion_store

        assert isinstance(local_publish_store, LocalObjectStore)
        self.local_publish_store = local_publish_store

        assert isinstance(sub_converted_store, WritableObjectStore)
        self.sub_converted_store = sub_converted_store

        assert isinstance(doc_converted_store, WritableObjectStore)
        self.doc_converted_store = doc_converted_store


    @retry(stop=stop_after_attempt(6), wait=wait_fixed(10))
    def download_source (self, payload: ConversionPayload) -> Tuple[str, LocalFileObj]:
        """
        Download the src files and return the main tex file
        """

        if isinstance(payload, DocumentConversionPayload):
            src = UngzippedFileObj(self.doc_src_store.to_obj(doc_src_path(payload)))
            print (f'SOURCE_PATH: {doc_src_path(payload)}')
        else:
            assert isinstance(payload, SubmissionConversionPayload)
            src = UngzippedFileObj(self.sub_src_store.to_obj(sub_src_path(payload)))

        with src.open('rb') as ungzip_file:
            input_bytes = ungzip_file.read()
            checksum = _get_checksum(input_bytes)
        
        if payload.single_file:
            with open(f'{self.local_conversion_store.prefix}{payload.name}.tex', 'wb+') as local_file:
                local_file.write(input_bytes)

            main_src_obj = self.local_conversion_store.to_obj(f'{payload.name}.tex')
            assert isinstance(main_src_obj, LocalFileObj)

            return checksum, main_src_obj

        with tarfile.open(fileobj=BytesIO(input_bytes)) as tar:
            tar.extractall(self.local_conversion_store.prefix+payload.name)

        in_dir = self.local_conversion_store.prefix+payload.name
        main_src = find_primary_tex(in_dir, ZeroZeroReadMe(in_dir))[0]
        print (f'MAIN SRC: {main_src}')

        main_src_obj = self.local_conversion_store.to_obj(os.path.relpath(f'{in_dir}/{main_src}', self.local_conversion_store.prefix))
        print (f'MAIN SRC OBJ: {main_src_obj}, ID: {payload.identifier}')
        assert isinstance(main_src_obj, LocalFileObj)

        return checksum, main_src_obj
    
    def latexml_output_dir_name (self, payload: ConversionPayload) -> str:
        return f'{self.local_conversion_store.prefix}{payload.name}/html/{payload.name}/'
    
    def _upload_dir_name (self, payload: ConversionPayload) -> str:
        return f'{self.local_conversion_store.prefix}{payload.name}/html/'
    
    def upload_latexml (self, payload: ConversionPayload) -> None:
        """
        Upload the latexml and metadata for the given payload. Delete the 
        working directory for the payload after.
        """
        src_dir = self._upload_dir_name(payload)
        if isinstance(payload, DocumentConversionPayload):
            print (f'Uploading to bucket: {self.doc_converted_store.bucket}')
            self.doc_converted_store.copy_local_dir(self.latexml_output_dir_name(payload), payload.name)
        else:
            destination_fname = f'{src_dir}{payload.name}.tar.gz'
            with tarfile.open(destination_fname, "w:gz") as tar:
                tar.add(f'{src_dir}/{payload.name}', arcname=str(payload.name))
            self.sub_converted_store.write_obj(LocalFileObj(Path(destination_fname)),
                                               self.sub_converted_store.bucket.blob(f'{payload.name}.tar.gz'))
        self.clean_up_conversion(payload)

    
    def remove_ltxml(self, payload: ConversionPayload) -> None:
        """
        Remove files with the .ltxml extension from the working
        directory of the payload
        """
        for root, _, files in os.walk(self.local_conversion_store.prefix+payload.name):
            for file in files:
                if str(file).endswith('.ltxml'):
                    os.remove(os.path.join(root, file))

    
    def clean_up_conversion (self, payload: ConversionPayload) -> None:
        shutil.rmtree(self.local_conversion_store.prefix+payload.name)

    def clean_up_publish (self, payload: PublishPayload) -> None:
        try:
            shutil.rmtree(self.local_publish_store.prefix+payload.submission_id)
        except:
            pass
        try:
            shutil.rmtree(self.local_publish_store.prefix+payload.paper_id.idv)
        except:
            pass

    def download_submission_conversion (self, payload: PublishPayload) -> None:
        # Download and expand submission conversion .tar.gz
        sub_conversion = UngzippedFileObj(
            self.sub_converted_store.to_obj(f'{payload.submission_id}.tar.gz'))
        with sub_conversion.open('rb') as ungzip_file:
            with tarfile.open(fileobj=ungzip_file) as tar: # type: ignore
                tar.extractall(self.local_publish_store.prefix)

        doc_path = f'{self.local_publish_store.prefix}{payload.paper_id.idv}'
        if os.path.exists(doc_path):
            shutil.rmtree(doc_path)
        os.rename(
            f'{self.local_publish_store.prefix}{payload.submission_id}',
            doc_path,
        )
        os.rename(
            f'{doc_path}/{payload.submission_id}.html',
            f'{doc_path}/{payload.paper_id.idv}.html'
        )

    # TODO: refactor so publish and convert can both use
    def upload_document_conversion (self, payload: PublishPayload) -> None:
        # Upload directory back
        self.doc_converted_store.copy_local_dir(self.local_publish_store.prefix+payload.paper_id.idv,
                                                payload.paper_id.idv)
        print (f'successfully uploaded to bucket for {payload}')

