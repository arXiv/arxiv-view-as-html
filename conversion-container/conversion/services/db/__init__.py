from typing import Optional, Tuple

from flask import current_app
from sqlalchemy.sql import text, select

from arxiv.db import session
from arxiv.db.models import Submission, Metadata

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
    license_raw = session.execute(
        select(Metadata.license)
        .filter(Metadata.paper_id == paper_id)
        .filter(Metadata.version == version)
    ).scalar()
    return _license_url_to_str_mapping(license_raw)
    
# @database_retry(5)
def get_license_for_submission (submission_id: int) -> str:
    license_raw = session.execute(
        select(Submission.license)
        .filter(Submission.submission_id == submission_id)
    ).scalar()
    return _license_url_to_str_mapping(license_raw)