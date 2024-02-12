from typing import Optional
from datetime import datetime
from contextlib import contextmanager
import logging

from flask import current_app

from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from sqlalchemy.exc import IntegrityError

from ..exceptions import DBConnectionError
from ..models.db import db, DBLaTeXMLDocuments, DBLaTeXMLSubmissions
from ..models.util import database_retry, transaction

logger = logging.getLogger(__name__)

@database_retry(3)
def submission_has_html (submission_id: int) -> Optional[DBLaTeXMLSubmissions]:
    with current_app.app_context():
        with transaction() as session:
            row = db.session.query(DBLaTeXMLSubmissions) \
                .filter(DBLaTeXMLSubmissions.submission_id == submission_id) \
                .first()
            return row if (row and row.conversion_status == 1) else None

@database_retry(3)
def write_published_html (paper_id: str, version: int, html_submission: DBLaTeXMLSubmissions):
    with current_app.app_context():
        with transaction() as session:
            try:
                row = DBLaTeXMLDocuments (
                    paper_id=paper_id,
                    document_version=version,
                    conversion_status=1,
                    latexml_version=html_submission.latexml_version,
                    tex_checksum=html_submission.tex_checksum,
                    conversion_start_time=html_submission.conversion_start_time,
                    conversion_end_time=html_submission.conversion_end_time,
                    publish_dt=datetime.utcnow()
                )
                session.merge(row)
                session.commit()
            except IntegrityError as e:
                logger.info(f'Integrity Error for {paper_id}, rolling back')
                session.rollback()


@database_retry(3)
def get_submission_timestamp (submission_id: int) -> Optional[str]:
    with current_app.app_context():
        with transaction() as session:
            query = text("SELECT submit_time from arXiv_submissions WHERE submission_id=:submission_id")
            query = query.bindparams(submission_id=submission_id)
            ts: datetime = session.execute(query).scalar() # TODO: Add error handling
            return ts.strftime('%d %b %Y')

@database_retry(3)
def get_version_primary_category (paper_id: str, version: int) -> Optional[str]:
    with current_app.app_context():
        with transaction() as session:
            query = text("SELECT abs_categories FROM arXiv_metadata WHERE paper_id=:paper_id AND version=:version")
            query = query.bindparams(paper_id=paper_id, version=version)
            return session.execute(query).scalar().split(' ')[0] # TODO: Needs to be tested