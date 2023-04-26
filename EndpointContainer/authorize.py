"""Authorization module for submission"""
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from arxiv_auth.legacy.util import is_configured, current_session
import exceptions

def authorize_user_for_submission(user_id: str, submission_id: str) -> bool:
    """
    Checks if the user is authorized to submit.

    Parameters
    ----------
    user_id : str
    submission_id : str
    
    Raises
    ------
    exceptions.DBConnectionError
    exceptions.DBConfigError
    """
    if is_configured():
        try:
            conn = current_session().connection()
            query = text("SELECT submitter_id FROM arXiv_submissions WHERE submission_id=:submission_id")
            query = query.bindparams(submission_id=submission_id)
            submitter_id = conn.execute(query).scalar()
            if submitter_id and int(submitter_id) == int(user_id):
                return True
            return False
        except Exception as exc:
            raise exceptions.DBConnectionError("DB Connection failed") from exc
    else:
        raise exceptions.DBConfigError("db not configured")

def submission_published(submission_id: str) -> bool:
    """
    Checks if the submission has been published before

    Parameters
    ----------
    submission_id : str

    Returns
    -------
    bool

    Raises
    ------
    exceptions.DBConnectionError
    exceptions.DBConfigError
    """
    if is_configured():
        try:
            conn = current_session().connection()
            query = text("SELECT status FROM arXiv_submissions WHERE submission_id=:submission_id")
            query = query.bindparams(submission_id=submission_id)
            status = conn.execute(query).scalar()
            print (f"STATUS: {status}")
            if int(status) == 7:
                return True
            return False # This probably shouldn't be an exception
        except Exception as exc:
            raise exceptions.DBConnectionError("DB Connection Failed") from exc
    else:
        raise exceptions.DBConfigError("DB Not Configured")
