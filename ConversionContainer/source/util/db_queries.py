from typing import Optional, Tuple

from flask import current_app
from sqlalchemy.sql import text

from ..models.util import transaction, database_retry

@database_retry(3)
def get_process_data_from_db (paper_id: str, version: int) -> Optional[Tuple[int, str]]:
    with current_app.app_context():
        with transaction() as session:
            query = text("SELECT submission_id, source_flags from arXiv_submissions WHERE doc_paper_id=:paper_id and version=:version")
            query = query.bindparams(paper_id=paper_id, version=version)
            row = session.execute(query).first()
            return row.tuple() if row else None