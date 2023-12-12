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


# @database_retry(5)
def submission_has_html (submission_id: int) -> Optional[DBLaTeXMLSubmissions]:
    with current_app.app_context():
        try:
            row = db.session.query(DBLaTeXMLSubmissions) \
                .filter(DBLaTeXMLSubmissions.submission_id == submission_id) \
                .first()
            return row if (row and row.conversion_status == 1) else None
        except Exception as e:
            logging.warn(str(e))
            # raise DBConnectionError from e
            raise e

@database_retry(3)
def write_published_html (paper_id: str, version: int, html_submission: DBLaTeXMLSubmissions):
    with current_app.app_context():
        try:
            row = DBLaTeXMLDocuments (
                paper_id=paper_id,
                document_version=version,
                conversion_status=1,
                latexml_version=html_submission.latexml_version,
                tex_checksum=html_submission.tex_checksum,
                conversion_start_time=html_submission.conversion_start_time,
                conversion_end_time=html_submission.conversion_end_time
            )
            db.session.add(row)
            db.session.commit()
            logging.info(f'Successfully wrote {paper_id} to db')         
        except IntegrityError as e:
            logging.info(f'{paper_id}v{version} has already been successfully processed with {str(e)}')
            db.session.rollback()
        except Exception as e:
            logging.warn(str(e))
            raise DBConnectionError from e

# @database_retry(5)
def get_submission_timestamp (submission_id: int) -> Optional[str]:
    with current_app.app_context():
        with transaction() as session:
            try:
                query = text("SELECT submit_time from arXiv_submissions WHERE submission_id=:submission_id")
                query = query.bindparams(submission_id=submission_id)
                ts: datetime = session.execute(query).scalar() # TODO: Add error handling
                return ts.strftime('%d %b %Y')
            except Exception as e:
                logging.warn(str(e))
                # raise DBConnectionError from e
                raise e

# @database_retry(5)
def get_version_primary_category (paper_id: str, version: int) -> Optional[str]:
    with current_app.app_context():
        try:
            query = text("SELECT abs_categories FROM arXiv_metadata WHERE paper_id=:paper_id AND version=:version")
            query = query.bindparams(paper_id=paper_id, version=version)
            return db.session.execute(query).scalar().split(' ')[0] # TODO: Needs to be tested
        except Exception as e:
            logging.info(str(e))
            # raise DBConnectionError from e
            raise e