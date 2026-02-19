import logging
from typing import List, Optional

from sqlalchemy.sql import text
from sqlalchemy.exc import OperationalError

from arxiv_auth.legacy.util import is_configured, current_session

from .db.util import database_retry

from .exceptions import DBConnectionError

@database_retry(3)
def get_source_format (arxiv_id: str, version: Optional[int] = None) -> Optional[str]:
    conn = current_session().connection()
    if version:
        query = text('SELECT source_format FROM arXiv_metadata WHERE paper_id=:id AND version=:v').\
                bindparams(id=arxiv_id, v=version)
    else:
        query = text('SELECT source_format, max(version) FROM arXiv_metadata WHERE paper_id=:id').\
                bindparams(id=arxiv_id)
    try:
        return conn.execute(query).fetchone()[0]
    except OperationalError:
        raise DBConnectionError
    except Exception as e:
        logging.info(str(e))
        return None