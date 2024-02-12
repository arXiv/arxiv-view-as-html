from typing import Any, Optional, Tuple
import hashlib
import os
import gzip
import logging
from flask import current_app

from google.cloud.storage.blob import Blob

from ..exceptions import DBConnectionError
from ..models.db import DBLaTeXMLDocuments, DBLaTeXMLSubmissions, db
from ..models.util import transaction, now, database_retry

logger = logging.getLogger(__name__)

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

def has_doc_been_tried (paper_idv: str) -> bool:
    paper_id, document_version = _get_id_version (paper_idv)
    rec = db.session.query(DBLaTeXMLDocuments) \
            .filter(DBLaTeXMLDocuments.paper_id == paper_id) \
            .filter(DBLaTeXMLDocuments.document_version == document_version) \
            .first()
    return rec is not None

@database_retry(5)
def _write_start_doc (paper_idv: str, tar_fpath: str):
    paper_id, document_version = _get_id_version (paper_idv)
    try:
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
    except Exception as e:
        raise DBConnectionError from e

@database_retry(5)
def _write_start_sub (submission_id: int, tar_fpath: str):
    try:
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
    except Exception as e:
        raise DBConnectionError from e


def write_start (id: Any, tar_fpath: str, is_submission: bool):
    if is_submission:
        _write_start_sub(int(id), tar_fpath)
    else:
        _write_start_doc(id, tar_fpath)

@database_retry(5)
def _write_success_doc (paper_idv: str, tar_fpath: str) -> bool:
    paper_id, document_version = _get_id_version (paper_idv)
    success = False
    try:
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
                        logger.info(f"document {paper_id}v{document_version} successfully written")
    except Exception as e:
        raise DBConnectionError from e
    if not success:
        logger.info(f"document {paper_id}v{document_version} failed to write")
    return success

@database_retry(5)
def _write_success_sub (submission_id: int, tar_fpath: str) -> bool:
    success = False
    try:
        with transaction() as session:
            obj = session.query(DBLaTeXMLSubmissions) \
                    .filter(int(submission_id) == DBLaTeXMLSubmissions.submission_id) \
                    .all()
            if len(obj) > 0:
                obj = obj[0]
                if obj.tex_checksum == _get_checksum(tar_fpath) and \
                    obj.latexml_version == _latexml_commit() and \
                    obj.conversion_status != 1:
                        obj.conversion_status = 1
                        obj.conversion_end_time = now()
                        success = True
                        logger.info(f"{submission_id}: Successfully written")
    except Exception as e:
        raise DBConnectionError from e
    if not success:
        logger.info(f"{submission_id}: Failed to write")
    return success

def write_success (id: int, tar_fpath: str, is_submission: bool):
    if is_submission:
        return _write_success_sub(int(id), tar_fpath)
    else:
        return _write_success_doc(id, tar_fpath)
    
@database_retry(5)
def _write_failure_doc (paper_idv: str, tar_fpath: str) -> bool:
    paper_id, document_version = _get_id_version (paper_idv)
    try:
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
                    logger.info(f"document {paper_id}v{document_version} conversion failure written")
    except Exception as e:
        raise DBConnectionError from e

@database_retry(5)
def _write_failure_sub (submission_id: int, tar_fpath: str) -> bool:
    try:
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
                    logger.info(f"{submission_id}: Conversion failure written")
    except Exception as e:
        raise DBConnectionError from e

def write_failure (id: int, tar_fpath: str, is_submission: bool):
    if is_submission:
        return _write_failure_sub(int(id), tar_fpath)
    else:
        return _write_failure_doc(id, tar_fpath)
