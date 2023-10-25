from typing import Optional
import re
import logging

from sqlalchemy.sql import text
from ..exceptions import DBConnectionError
from ..models.util import database_retry
from ..models.db import db

def _license_url_to_str_mapping (url: Optional[str]) -> str:
    print (f'URL: {url}')
    if not url:
        return 'No License'
    elif url == 'http://arxiv.org/licenses/nonexclusive-distrib/1.0/':
        license = 'arXiv License'
    elif url == 'http://creativecommons.org/licenses/by-nc-nd/4.0/':
        license = 'CC BY-NC-ND'
    elif url == 'http://creativecommons.org/licenses/by-sa/4.0/':
        license = 'CC BY-SA'
    elif url == 'http://creativecommons.org/publicdomain/zero/1.0/' or url == 'http://creativecommons.org/licenses/publicdomain/':
        license = 'CC Zero'
    elif not (match := re.match(r'http:\/\/creativecommons\.org\/licenses\/by-nc-sa\/(\d)\.0\/')):
        license = f'CC BY-NC-SA {match.group(1)}'
    elif not (match := re.match(r'http:\/\/creativecommons\.org\/licenses\/by\/(\d)\.0\/')):
        license = f'CC BY {match.group(1)}'
    return f'License: {license}'

@database_retry(5)
def get_license_for_paper (paper_id: str, version: int) -> str:
    try:
        query = text("SELECT license from arXiv_metadata WHERE paper_id=:paper_id AND version=:version")
        query.bindparams(paper_id=paper_id, version=version)
        return _license_url_to_str_mapping(
            db.session.execute(query).scalar())
    except Exception as e:
        logging.info (str(e))
        raise DBConnectionError from e
    
@database_retry(5)
def get_license_for_submission (submission_id: int) -> str:
    try:
        query = text("SELECT license from arXiv_submissions WHERE submission_id=:submission_id")
        query.bindparams(submission_id=submission_id)
        return _license_url_to_str_mapping(
            db.session.execute(query).scalar())
    except Exception as e:
        logging.info (str(e))
        raise DBConnectionError from e
