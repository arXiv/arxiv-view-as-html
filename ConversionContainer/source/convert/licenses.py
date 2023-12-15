from typing import Optional
import re
import logging

from sqlalchemy.sql import text
from ..exceptions import DBConnectionError
from ..models.util import database_retry, transaction
from ..models.db import db

def _license_url_to_str_mapping (url: Optional[str]) -> str:
    if not url:
        return 'No License'
    elif url == 'http://arxiv.org/licenses/nonexclusive-distrib/1.0/':
        license = 'arXiv.org perpetual non-exclusive license'
    elif url == 'http://creativecommons.org/licenses/by-nc-nd/4.0/':
        license = 'CC BY-NC-ND 4.0'
    elif url == 'http://creativecommons.org/licenses/by-sa/4.0/':
        license = 'CC BY-SA 4.0'
    elif url == 'http://creativecommons.org/publicdomain/zero/1.0/' or url == 'http://creativecommons.org/licenses/publicdomain/':
        license = 'CC Zero'
    elif (match := re.match(r'http:\/\/creativecommons\.org\/licenses\/by-nc-sa\/(\d\.0)\/', url)):
        license = f'CC BY-NC-SA {match.group(1)}'
    elif (match := re.match(r'http:\/\/creativecommons\.org\/licenses\/by\/(\d\.0)\/', url)):
        license = f'CC BY {match.group(1)}'
    logging.warn(f'License not raw: License: {license}')
    return f'License: {license}'

@database_retry(5)
def get_license_for_paper (paper_id: str, version: int) -> str:
    query = text("SELECT license from arXiv_metadata WHERE paper_id=:paper_id AND version=:version")
    query = query.bindparams(paper_id=paper_id, version=version)
    with transaction() as session:
        license_raw = session.execute(query).scalar()
    return _license_url_to_str_mapping(license_raw)
    
@database_retry(5)
def get_license_for_submission (submission_id: int) -> str:
    query = text("SELECT license from arXiv_submissions WHERE submission_id=:submission_id")
    query = query.bindparams(submission_id=submission_id)
    with transaction() as session:
        license_raw = session.execute(query).scalar()
    return _license_url_to_str_mapping(license_raw)

