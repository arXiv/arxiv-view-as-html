import logging
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.sql import text

from arxiv_auth.legacy.util import is_configured, current_session

from .exceptions import DBConnectionError, \
    DBConfigError, UnauthorizedError

def _get_arxiv_mod_user_ids () -> List[str]:
    conn = current_session().connection()
    query = text("SELECT user_id FROM arXiv_moderators")
    return [int(row['user_id']) for row in conn.execute(query).fetchall()]

def _get_arxiv_admin_user_ids () -> List[str]:
    conn = current_session().connection()
    query = text("SELECT user_id FROM tapir_users WHERE flag_edit_users = 1")
    return [int(row['user_id']) for row in conn.execute(query).fetchall()]

def authorize_user_for_submission(user_id: str, submission_id: str):
    """
    Checks if the user is authorized to submit. Returns None if successful,
    raise exception otherwise

    Parameters
    ----------
    user_id : str
    submission_id : str
    
    Raises
    ------
    DBConnectionError
    DBConfigError
    UnauthorizedError
    """
    if is_configured():
        try:
            logging.info('Made DB call')
            conn = current_session().connection()
            query = text("SELECT submitter_id FROM arXiv_submissions WHERE submission_id=:submission_id")
            query = query.bindparams(submission_id=submission_id)
            submitter_id = conn.execute(query).scalar()

            if submitter_id and int(submitter_id) == int(user_id):
                return
            if int(user_id) in _get_arxiv_mod_user_ids():
                return
            if int(user_id) in _get_arxiv_admin_user_ids():
                return
        except Exception as exc:
            logging.warning('DB Connection Failed')
            raise DBConnectionError("DB Connection failed") from exc
        raise UnauthorizedError
    
    logging.warning('DB Not Configured')
    raise DBConfigError("db not configured")

    