import logging
from typing import List

from sqlalchemy.sql import text

from arxiv_auth.legacy.util import is_configured, current_session

from .db.util import database_retry

from .exceptions import DBConnectionError, \
    DBConfigError, UnauthorizedError

def is_editor (user_id: int) -> bool:
    conn = current_session().connection()
    query = text("SELECT user_id FROM tapir_users WHERE flag_edit_users = 1 and user_id=:user_id") \
        .bindparams(user_id=user_id)
    return conn.execute(query).scalar() is not None

def is_moderator (user_id: int) -> bool:
    conn = current_session().connection()
    query = text("SELECT user_id FROM arxiv_moderators WHERE user_id=:user_id") \
        .bindparams(user_id=user_id)
    return conn.execute(query).scalar() is not None

@database_retry(5)
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
            query = text("SELECT submitter_id, is_withdrawn, status FROM arXiv_submissions WHERE submission_id=:submission_id") \
                .bindparams(submission_id=submission_id)
            row = current_session().connection().execute(query).first()

            if row:
                submitter_id, is_withdrawn, status = row.tuple()
            else:
                logging.warning(f'Cannot find row for submission_id: {submission_id}')
                raise DBConfigError
            
            # Check for editor / moderator first so they can still see deleted papers
            if is_editor(user_id) or is_moderator(user_id):
                return

            if submitter_id and int(submitter_id) == int(user_id) \
                and not is_withdrawn and status < 9:
                return
        except Exception as exc:
            logging.warning(str(exc))
            logging.warning('DB Connection Failed')
            raise DBConnectionError("DB Connection failed") from exc
        raise UnauthorizedError
    
    logging.warning('DB Not Configured')
    raise DBConfigError("db not configured")

    