from typing import Any, Optional, Tuple
import hashlib
import os
import gzip
import logging
from flask import current_app

from google.cloud.storage.blob import Blob

from ..models.db import DBLaTeXMLDocuments, DBLaTeXMLSubmissions
from ..models.util import transaction, now

def _latexml_commit (): return current_app.config['LATEXML_COMMIT']

def _get_id_version (paper_idv: str) -> Tuple[str, int]:
    parts = paper_idv.split('v')
    return parts[0], int(parts[1])

def _get_checksum (abs_fname: str) -> str:
    md5_hash = hashlib.md5()
    with gzip.open(abs_fname, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            md5_hash.update(byte_block)
    return md5_hash.hexdigest()

def _write_start_doc (paper_idv: str, tar_fpath: str):
    paper_id, document_version = _get_id_version (paper_idv)
    with transaction() as session:
        rec = session.query(DBLaTeXMLDocuments) \
                .filter(DBLaTeXMLDocuments.paper_id == paper_id) \
                .filter(DBLaTeXMLDocuments.document_version == document_version) \
                .first()
        if not rec:
            rec = DBLaTeXMLDocuments (
                paper_id=paper_id,
                document_version=document_version,
                conversion_status=0, # 0 for in progress, 1 for success, 2 for failure
                latexml_version=_latexml_commit(),
                tex_checksum=_get_checksum(tar_fpath),
                conversion_start_time=now()
            )
            session.add(rec)
        else:
            rec.conversion_status = 0
            rec.latexml_version = _latexml_commit()
            rec.tex_checksum = _get_checksum(tar_fpath)
            rec.conversion_start_time = now()

    logging.info(f"Conversion started for document {paper_id}v{document_version}")


def _write_start_sub (submission_id: int, tar_fpath: str):
    with transaction() as session:
        rec = session.query(DBLaTeXMLSubmissions) \
                .filter(DBLaTeXMLSubmissions.submission_id == submission_id) \
                .first()
        if not rec:
            rec = DBLaTeXMLSubmissions (
                submission_id=submission_id,
                conversion_status=0, # 0 for in progress, 1 for success, 2 for failure
                latexml_version=_latexml_commit(),
                tex_checksum=_get_checksum(tar_fpath),
                conversion_start_time=now()
            )
            session.add(rec)
        else:
            rec.conversion_status = 0
            rec.latexml_version = _latexml_commit()
            rec.tex_checksum = _get_checksum(tar_fpath)
            rec.conversion_start_time = now()

    logging.info(f"{now()}: Conversion started for submission {submission_id}")


def write_start (id: Any, tar_fpath: str, is_submission: bool):
    logging.info(f"{now()}: Trying write start for {tar_fpath}")
    if is_submission:
        _write_start_sub(int(id), tar_fpath)
    else:
        _write_start_doc(id, tar_fpath)


def _write_success_doc (paper_idv: str, tar_fpath: str) -> bool:
    paper_id, document_version = _get_id_version (paper_idv)
    success = False
    with transaction() as session:
        obj = session.query(DBLaTeXMLDocuments) \
                .filter(DBLaTeXMLDocuments.paper_id == paper_id) \
                .filter(DBLaTeXMLDocuments.document_version == document_version) \
                .all()
        if len(obj) > 0:
            obj = obj[0]
            if obj.tex_checksum == _get_checksum(tar_fpath) and \
                obj.latexml_version == _latexml_commit() and \
                obj.conversion_status != 1:
                    obj.conversion_status = 1
                    obj.conversion_end_time = now()
                    success = True
                    logging.info(f"{now()}: document {paper_id}v{document_version} successfully written")
    if not success:
        logging.info(f"{now()}: document {paper_id}v{document_version} failed to write")
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
                obj.latexml_version == _latexml_commit() and \
                obj.conversion_status != 1:
                    obj.conversion_status = 1
                    obj.conversion_end_time = now()
                    success = True
                    logging.info(f"{now()}: document {submission_id} successfully written")
    if not success:
        logging.info(f"{now()}: document {submission_id} failed to write")
    return success

def write_success (id: int, tar_fpath: str, is_submission: bool):
    if is_submission:
        return _write_success_sub(int(id), tar_fpath)
    else:
        return _write_success_doc(id, tar_fpath)
    
def _write_failure_doc (paper_idv: str, tar_fpath: str) -> bool:
    paper_id, document_version = _get_id_version (paper_idv)
    with transaction() as session:
        obj = session.query(DBLaTeXMLDocuments) \
                .filter(DBLaTeXMLDocuments.paper_id == paper_id) \
                .filter(DBLaTeXMLDocuments.document_version == document_version) \
                .all()
        if len(obj) > 0:
            obj = obj[0]
            if obj.tex_checksum == _get_checksum(tar_fpath) and \
                obj.latexml_version == _latexml_commit():
                obj.conversion_status = 2
                obj.conversion_end_time = now()
                logging.info(f"{now()}: document {paper_id}v{document_version} conversion failure written")

def _write_failure_sub (submission_id: int, tar_fpath: str) -> bool:
    with transaction() as session:
        obj = session.query(DBLaTeXMLSubmissions) \
                .filter(DBLaTeXMLSubmissions.submission_id == submission_id) \
                .all()
        if len(obj) > 0:
            obj = obj[0]
            if obj.tex_checksum == _get_checksum(tar_fpath) and \
                obj.latexml_version == _latexml_commit():
                obj.conversion_status = 2
                obj.conversion_end_time = now()
                logging.info(f"{now()}: document {submission_id} conversion failure written")

def write_failure (id: int, tar_fpath: str, is_submission: bool):
    if is_submission:
        return _write_failure_sub(int(id), tar_fpath)
    else:
        return _write_failure_doc(id, tar_fpath)
