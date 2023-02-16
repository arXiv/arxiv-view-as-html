from sqlalchemy.orm import sessionmaker

from arxiv_auth.legacy.util import is_configured, current_session

import config
from Submissions import Submissions

def authorize_user_for_submission (user_id, submission_id) -> bool:
    if is_configured():
        submitter_id = current_session().query(Submissions.submitter_id) \
                        .filter(Submissions.submission_id == submission_id) \
                        .scalar()
        if submitter_id and submitter_id == user_id:
            return True
    return False # Maybe want to separate failed authorization from failure to connect to DB