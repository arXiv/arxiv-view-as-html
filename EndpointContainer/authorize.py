from sqlalchemy import create_engine
from sqlalchemy.sql import text

from arxiv_auth.legacy.util import is_configured, current_session

import config

import logging
import google.cloud.logging

client = google.cloud.logging.Client()
client.setup_logging()

def authorize_user_for_submission (user_id, submission_id) -> bool:
    if is_configured():
        try:
            conn = current_session().connection()
            query = text("SELECT submitter_id FROM arXiv_submissions WHERE submission_id=:submission_id")
            query = query.bindparams(submission_id=submission_id)
            submitter_id = conn.execute(query).scalar()
            if submitter_id and int(submitter_id) == int(user_id):
                return True
            return False
        except:
            raise Exception ("DB Connection failed")
    else:
        raise Exception ("db not configured")

def submission_published (submission_id) -> bool:
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
        except:
            raise Exception("DB Connection Failed")
    else:
        raise Exception ("db not configured")
        
