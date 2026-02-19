from typing import Optional
import logging

from flask import Response

from arxiv_auth.legacy.models import db

from .db.models import DBLaTeXMLSubmissions
from .db.util import database_retry
from .exceptions import DBConnectionError
# from flask_sqlalchemy import 

@database_retry(5)
def _get_latexml_status_for_document (submission_id: int) -> Optional[int]:
    """Get latexml conversion status for a given paper_id and version"""
    try:
        return db.session.query(DBLaTeXMLSubmissions.conversion_status) \
            .filter(DBLaTeXMLSubmissions.submission_id == submission_id) \
            .scalar()
    except Exception as e:
        raise DBConnectionError from e
    
def poll_submission (submission_id) -> Response:
    try:
        conversion_status = _get_latexml_status_for_document(submission_id)
        logging.info(f'TYPE: {type(conversion_status)}')
        logging.info(f'VALUE: {conversion_status}')
        if conversion_status == 1:
            return {'exists': True}, 200
        return {'exists': False}, 200
    except DBConnectionError:
        return {'exists': False}, 500
