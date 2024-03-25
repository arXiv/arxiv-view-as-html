from typing import Optional, Tuple
from datetime import datetime
import logging

from flask import current_app
from sqlalchemy.sql import select
from sqlalchemy.exc import IntegrityError

from arxiv.identifier import Identifier
from arxiv.db import session, transaction
from arxiv.db.models import (
    Submission, 
    Metadata, 
    DBLaTeXMLDocuments,
    DBLaTeXMLSubmissions
)

from ...domain.conversion import ConversionPayload, DocumentConversionPayload
from ...formatting import license_url_to_str_mapping
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
    return license_url_to_str_mapping(license_raw)
    
# @database_retry(5)
def get_license_for_submission (submission_id: int) -> str:
    license_raw = session.execute(
        select(Submission.license)
        .filter(Submission.submission_id == submission_id)
    ).scalar()
    return license_url_to_str_mapping(license_raw)

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
        obj = obj
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
                .one()
        if obj.tex_checksum == checksum and \
            obj.latexml_version == current_app.config['LATEXML_COMMIT']:
            obj.conversion_status = 2
            obj.conversion_end_time = now()

# @database_retry(5)
def _write_failure_sub (submission_id: int, checksum: str) -> bool:
    with transaction() as session:
        obj = session.query(DBLaTeXMLSubmissions) \
                .filter(DBLaTeXMLSubmissions.submission_id == submission_id) \
                .one()
        if obj.tex_checksum == checksum and \
            obj.latexml_version == current_app.config['LATEXML_COMMIT']:
            obj.conversion_status = 2
            obj.conversion_end_time = now()


def write_failure (payload: ConversionPayload, checksum: str):
    if isinstance(payload, DocumentConversionPayload):
        return _write_failure_doc(payload.identifier, checksum)
    else:
        return _write_failure_sub(payload.identifier, checksum)
    

# @database_retry(3)
def get_submission_with_html (submission_id: int) -> Optional[DBLaTeXMLSubmissions]:
    row = session.scalar(
        select(DBLaTeXMLSubmissions) \
        .filter(DBLaTeXMLSubmissions.submission_id == submission_id) \
        .first()
    )
    return row if (row and row.conversion_status == 1) else None


# @database_retry(3)
def write_published_html (identifier: Identifier, html_submission: DBLaTeXMLSubmissions):
    with transaction() as session:
        # try:
        row = DBLaTeXMLDocuments (
            paper_id=identifier.id,
            document_version=identifier.version,
            conversion_status=1,
            latexml_version=html_submission.latexml_version,
            tex_checksum=html_submission.tex_checksum,
            conversion_start_time=html_submission.conversion_start_time,
            conversion_end_time=html_submission.conversion_end_time,
            publish_dt=datetime.utcnow()
        )
        session.merge(row)
        # except IntegrityError as e:
        #     logging.info(f'Integrity Error for {paper_id}, rolling back')
        #     session.rollback()


# @database_retry(3)
def get_submission_timestamp (submission_id: int) -> Optional[str]:
    timestamp = session.scalar(
        select(Submission.submit_time)
        .filter(Submission.submission_id == submission_id)
    )
    return timestamp.strftime('%d %b %Y') if timestamp else None

# @database_retry(3)
def get_submission_timestamp_from_arxiv_identifier (identifier: Identifier) -> Optional[str]:
    timestamp = session.scalar(
        select(Submission.submit_time)
        .filter(Submission.doc_paper_id == identifier.id)
        .filter(Submission.version == identifier.version)
    )
    return timestamp.strftime('%d %b %Y') if timestamp else None

# @database_retry(3)
def get_version_primary_category (identifier: Identifier) -> Optional[str]:
    row = session.scalar(
        select(Metadata.abs_categories)
        .filter(Metadata.paper_id == identifier.id)
        .filter(Metadata.version == identifier.version)
    )
    return row.split(' ')[0] if row else None