from sqlalchemy import create_engine
from sqlalchemy.sql import text

from arxiv_auth.legacy.util import is_configured, current_session

import config

def authorize_user_for_submission (user_id, submission_id) -> bool:
    if is_configured():
        # submitter_id = current_session().query(Submissions.submitter_id) \
        #                 .filter(Submissions.submission_id == submission_id) \
        #                 .scalar()
        with current_session().connection() as conn:
            query = text("SELECT submitter_id FROM arXiv_submissions WHERE submission_id=:submission_id")
            query = query.bindparams(submission_id=submission_id)
            submitter_id = conn.execute(query).scalar()
        if submitter_id and submitter_id == user_id:
            return True
    else:
        raise Exception ("db not configured")
    return False # Maybe want to separate failed authorization from failure to connect to DB

def submission_published (submission_id) -> bool:
    submission_id_no_dot = int(submission_id.replace('.', ''))
    if is_configured():
        with current_session().connection() as conn:
            query = text("SELECT status FROM arXiv_submissions WHERE submission_id=:submission_id")
            query = query.bindparams(submission_id=submission_id_no_dot)
            status = conn.execute(query).scalar()
            print (f"STATUS: {status}")
        if int(status) == 7:
            return True
        raise Exception(f"STATUS: {status}")
    else:
        raise Exception ("db not configured")
    return False
        
