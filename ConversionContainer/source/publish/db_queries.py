from typing import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from ..exceptions import DBConnectionError
from ..models.db import DBLaTeXMLDocuments, DBLaTeXMLSubmissions
from ..models.util import database_retry


@database_retry(5)
def submission_has_html (submission_id: int, session: Session) -> DBLaTeXMLSubmissions:
    row = session.query(DBLaTeXMLSubmissions) \
        .filter(DBLaTeXMLSubmissions.submission_id == submission_id) \
        .first()
    return row if (row and row.conversion_status == 1) else None

@database_retry(5)
def write_published_html (paper_id: str, version: int, html_submission: DBLaTeXMLSubmissions, session: Session):
    row = DBLaTeXMLDocuments (
        paper_id=paper_id,
        document_version=version,
        conversion_status=1,
        latexml_version=html_submission.latexml_version,
        tex_checksum=html_submission.tex_checksum,
        conversion_start_time=html_submission.conversion_start_time,
        conversion_end_time=html_submission.conversion_end_time
    )
    session.add(row)
