from typing import Optional, Tuple

from flask import current_app
from sqlalchemy.sql import text, select

from arxiv.identifier import Identifier
from arxiv.db import session, transaction
from arxiv.db.models import (
    Submission, 
    Metadata, 
    DBLaTeXMLDocuments,
    DBLaTeXMLSubmissions
)

from ...domain.conversion import ConversionPayload, DocumentConversionPayload
from ...formatting import _license_url_to_str_mapping
from .util import now

# @database_retry(3)
def get_process_data_from_db (paper_id: str, version: int) -> Optional[Tuple[int, str]]:
    return session.scalar(
            select (Submission.submission_id, Submission.source_flags)
            .filter(Submission.doc_paper_id == paper_id)
            .filter(Submission.version == version)
          )
        
# @database_retry(3)
def get_source_flags_for_submission (sub_id: int) -> Optional[str]:
    return session.scalar(
        select(Submission.source_flags)
        .filter(Submission.submission_id == sub_id)
    )

# @database_retry(5)
def get_license_for_paper (identifier: Identifier) -> str:
    license_raw = session.execute(
        select(Metadata.license)
        .filter(Metadata.paper_id == identifier.id)
        .filter(Metadata.version == identifier.version)
    ).scalar()
    return _license_url_to_str_mapping(license_raw)
    
# @database_retry(5)
def get_license_for_submission (submission_id: int) -> str:
    license_raw = session.execute(
        select(Submission.license)
        .filter(Submission.submission_id == submission_id)
    ).scalar()
    return _license_url_to_str_mapping(license_raw)

def has_doc_been_tried (identifier: Identifier) -> bool:
    rec = session.query(DBLaTeXMLDocuments) \
            .filter(DBLaTeXMLDocuments.paper_id == identifier.id) \
            .filter(DBLaTeXMLDocuments.document_version == identifier.version) \
            .first()
    return rec is not None

# @database_retry(5)
def _write_start_doc (identifier: Identifier, checksum: str):
    paper_id = identifier.id
    version = identifier.version
    with transaction() as session:
        rec = session.query(DBLaTeXMLDocuments) \
                .filter(DBLaTeXMLDocuments.paper_id == paper_id) \
                .filter(DBLaTeXMLDocuments.document_version == version) \
                .first()
        if not rec:
            rec = DBLaTeXMLDocuments (
                paper_id=paper_id,
                document_version=version,
                conversion_status=0, # 0 for in progress, 1 for success, 2 for failure
                latexml_version=current_app.config['LATEXML_COMMIT'],
                tex_checksum=checksum,
                conversion_start_time=now()
            )
            session.add(rec)
        else:
            rec.conversion_status = 0
            rec.latexml_version = current_app.config['LATEXML_COMMIT']
            rec.tex_checksum = checksum
            rec.conversion_start_time = now()

# @database_retry(5)
def _write_start_sub (submission_id: int, checksum: str):
    with transaction() as session:
        rec = session.query(DBLaTeXMLSubmissions) \
                .filter(DBLaTeXMLSubmissions.submission_id == submission_id) \
                .first()
        if not rec:
            rec = DBLaTeXMLSubmissions (
                submission_id=submission_id,
                conversion_status=0, # 0 for in progress, 1 for success, 2 for failure
                latexml_version=current_app.config['LATEXML_COMMIT'],
                tex_checksum=checksum,
                conversion_start_time=now()
            )
            session.add(rec)
        else:
            rec.conversion_status = 0
            rec.latexml_version = current_app.config['LATEXML_COMMIT']
            rec.tex_checksum = checksum
            rec.conversion_start_time = now()


def write_start (payload: ConversionPayload, checksum: str):
    if isinstance(payload, DocumentConversionPayload):
        _write_start_doc(payload.identifier, checksum)
    else:
        _write_start_sub(payload.identifier, checksum)


# @database_retry(5)
def _write_success_doc (identifier: Identifier, checksum: str) -> bool:
    with transaction() as session:
        obj = session.query(DBLaTeXMLDocuments) \
                .filter(DBLaTeXMLDocuments.paper_id == identifier.paper_id) \
                .filter(DBLaTeXMLDocuments.document_version == identifier.version) \
                .one()
        if obj.tex_checksum == checksum and \
            obj.latexml_version == current_app.config['LATEXML_COMMIT'] and \
            obj.conversion_status != 1:
                obj.conversion_status = 1
                obj.conversion_end_time = now()

# @database_retry(5)
def _write_success_sub (submission_id: int, checksum: str) -> bool:
    with transaction() as session:
        obj = session.query(DBLaTeXMLSubmissions) \
                .filter(int(submission_id) == DBLaTeXMLSubmissions.submission_id) \
                .one()
        obj = obj[0]
        if obj.tex_checksum == checksum and \
            obj.latexml_version == current_app.config['LATEXML_COMMIT'] and \
            obj.conversion_status != 1:
                obj.conversion_status = 1
                obj.conversion_end_time = now()


def write_success (payload: ConversionPayload, checksum: str):
    if isinstance(payload, DocumentConversionPayload):
        return _write_success_doc(payload.identifier, checksum)
    else:
        return _write_success_sub(payload.identifier, checksum)
    

# @database_retry(5)
def _write_failure_doc (identifier: Identifier, checksum: str) -> bool:
    with transaction() as session:
        obj = session.query(DBLaTeXMLDocuments) \
                .filter(DBLaTeXMLDocuments.paper_id == identifier.id) \
                .filter(DBLaTeXMLDocuments.document_version == identifier.version) \
                .all()
        if len(obj) > 0:
            obj = obj[0]
            if obj.tex_checksum == checksum and \
                obj.latexml_version == current_app.config['LATEXML_COMMIT']:
                obj.conversion_status = 2
                obj.conversion_end_time = now()

# @database_retry(5)
def _write_failure_sub (submission_id: int, checksum: str) -> bool:
    with transaction() as session:
        obj = session.query(DBLaTeXMLSubmissions) \
                .filter(DBLaTeXMLSubmissions.submission_id == submission_id) \
                .all()
        if len(obj) > 0:
            obj = obj[0]
            if obj.tex_checksum == checksum and \
                obj.latexml_version == current_app.config['LATEXML_COMMIT']:
                obj.conversion_status = 2
                obj.conversion_end_time = now()


def write_failure (payload: ConversionPayload, checksum: str):
    if isinstance(payload, DocumentConversionPayload):
        return _write_failure_doc(payload.identifier, checksum)
    else:
        return _write_failure_sub(payload.identifier, checksum)