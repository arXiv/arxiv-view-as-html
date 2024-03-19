from typing import Optional, Tuple

from flask import current_app
from sqlalchemy.sql import text, select

from arxiv.db import session
from arxiv.db.models import Submission

from ...formatting import _license_url_to_str_mapping

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
def get_license_for_paper (paper_id: str, version: int) -> str:
    query = text("SELECT license from arXiv_metadata WHERE paper_id=:paper_id AND version=:version")
    query = query.bindparams(paper_id=paper_id, version=version)
    license_raw = session.execute(query).scalar()
    return _license_url_to_str_mapping(license_raw)
    
# @database_retry(5)
def get_license_for_submission (submission_id: int) -> str:
    query = text("SELECT license from arXiv_submissions WHERE submission_id=:submission_id")
    query = query.bindparams(submission_id=submission_id)
    license_raw = session.execute(query).scalar()
    return _license_url_to_str_mapping(license_raw)