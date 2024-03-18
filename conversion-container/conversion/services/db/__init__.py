from typing import Optional, Tuple

from flask import current_app
from sqlalchemy.sql import text, select

from arxiv.db import session
from arxiv.db.models import Submission

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