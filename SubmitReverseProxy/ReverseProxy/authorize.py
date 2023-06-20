import logging

from sqlalchemy import create_engine
from sqlalchemy.sql import text

from arxiv_auth.legacy.util import is_configured, current_session

from .exceptions import DBConnectionError, \
    DBConfigError, UnauthorizedError

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
        except Exception as exc:
            logging.warning('DB Connection Failed')
            raise DBConnectionError("DB Connection failed") from exc
        if submitter_id and int(submitter_id) == int(user_id):
            return
        raise UnauthorizedError
    logging.warning('DB Not Configured')
    raise DBConfigError("db not configured")
    