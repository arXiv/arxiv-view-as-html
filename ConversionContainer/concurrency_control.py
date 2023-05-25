from typing import Any, Optional
import hashlib
import os
from flask import current_app

from models.db import DBLaTeXMLDocuments, DBLaTeXMLSubmissions
from models.util import transaction, now, current_session

from sqlalchemy import cast

from google.cloud.storage.blob import Blob

import logging
import google.cloud.logging

client = google.cloud.logging.Client()
client.setup_logging()

# TODO: Separate check to write from writing success

def _get_checksum (abs_fname: str) -> str:
    md5_hash = hashlib.md5()
    with open(abs_fname,"rb") as f:
        for byte_block in iter(lambda: f.read(4096),b""):
            md5_hash.update(byte_block)
    return md5_hash.hexdigest()

def _write_start_doc (document_id: int, document_version: int, tar_fpath: str):
    with transaction() as session:
        rec = DBLaTeXMLDocuments (
            document_id=document_id,
            document_version=document_version,
            conversion_status=0, # 0 for in progress, 1 for success, 2 for failure
            latexml_version=os.environ.get('LATEXML_COMMIT'),
            tex_checksum=_get_checksum(tar_fpath),
            conversion_start_time=now()
        )
        session.add(rec)
    logging.info(f"Conversion started for document {document_id}v{document_version}")


def _write_start_sub (submission_id: int, tar_fpath: str):
    with transaction() as session:
        rec = DBLaTeXMLSubmissions (
            submission_id=submission_id,
            conversion_status=0, # 0 for in progress, 1 for success, 2 for failure
            latexml_version=os.environ.get('LATEXML_COMMIT'),
            tex_checksum=_get_checksum(tar_fpath),
            conversion_start_time=now()
        )
        session.add(rec)
    logging.info(f"{now()}: Conversion started for submission {submission_id}")


def write_start (id: int, tar_fpath: str, version: Optional[int] = None):
    logging.info(f"{now()}: Trying write start for {tar_fpath}")
    if version is not None:
        _write_start_doc(id, version, tar_fpath)
    else:
        _write_start_sub(id, tar_fpath)

def _write_success_doc (document_id: int, document_version: int, tar_fpath: str) -> bool:
    success = False
    with transaction() as session:
        obj = session.query(DBLaTeXMLDocuments) \
                .filter(DBLaTeXMLDocuments.document_id == document_id) \
                .filter(DBLaTeXMLDocuments.document_version == document_version) \
                .all()
        if len(obj) > 0:
            obj = obj[0]
            if obj.tex_checksum == _get_checksum(tar_fpath) and \
                obj.latexml_version == os.environ.get('LATEXML_COMMIT') and \
                obj.conversion_status != 1:
                    obj.conversion_status = 1
                    obj.conversion_end_time = now()
                    success = True
                    logging.info(f"{now()}: document {document_id}v{document_version} successfully written")
    if not success:
        logging.info(f"{now()}: document {document_id}v{document_version} failed to write")
    return success

def _write_success_sub (submission_id: int, tar_fpath: str) -> bool:
    success = False
    with transaction() as session:
        obj = session.query(DBLaTeXMLSubmissions) \
                .filter(int(submission_id) == DBLaTeXMLSubmissions.submission_id) \
                .all()
        # logging.log(f'We got the object, here\'s the checksum: {obj[0].tex_checksum}')
        if len(obj) > 0:
            obj = obj[0]
            if obj.tex_checksum == _get_checksum(tar_fpath) and \
                obj.latexml_version == os.environ.get('LATEXML_COMMIT') and \
                obj.conversion_status != 1:
                    obj.conversion_status = 1
                    obj.conversion_end_time = now()
                    success = True
                    logging.info(f"{now()}: document {submission_id} successfully written")
    if not success:
        logging.info(f"{now()}: document {submission_id} failed to write")
    return success

def write_success (id: int, tar_fpath: str, version: Optional[int] = None):
    if version is not None:
        return _write_success_doc(id, version, tar_fpath)
    else:
        return _write_success_sub(id, tar_fpath)

