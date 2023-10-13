import logging
from typing import List, Optional

from sqlalchemy.sql import text
from sqlalchemy.exc import OperationalError

from arxiv_auth.legacy.util import is_configured, current_session

from .db.util import database_retry

from .exceptions import DBConnectionError

@database_retry(5)
def get_source_format (arxiv_id: str, version: Optional[int] = None) -> Optional[str]:
    conn = current_session().connection()
    if version:
        query = text('SELECT source_format FROM arXiv_documents WHERE paper_id=:id AND version=:v')
    else:
        query = text('SELECT source_format FROM arXiv_documents WHERE paper_id=:id AND version=:v')
    try:
        return conn.execute(query, id=arxiv_id, v=version).fetchone()['source_format']
    except OperationalError:
        raise DBConnectionError
    except:
        return None