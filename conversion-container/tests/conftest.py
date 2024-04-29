import pytest

from flask import Flask

from arxiv.files.object_store import LocalObjectStore
from conversion.factory import create_web_app
from conversion.services.files.writable_obj_store import WritableGSObjectStore

LATEXML_DB_URI = 'sqlite:///:memory:?cache=latexml'
CLASSIC_DATABASE_URI = 'sqlite:///:memory:'

TESTING_CONFIG = {
    'SUBMISSION_SOURCE_BUCKET': 'tests/data/submission-data/',
    'DOCUMENT_SOURCE_BUCKET': 'tests/data/document-data/',
    'SUBMISSION_CONVERTED_BUCKET': 'tests/data/submission-conversions/',
    'DOCUMENT_CONVERTED_BUCKET': 'tests/data/document-conversions/',

    'CLASSIC_DATABASE_URI': 'sqlite:///:memory:',

    'QA_BUCKET_SUB': 'tests/data/qa-sub/',
    'QA_BUCKET_DOC': 'tests/data/qa-doc/',

    'LATEXML_COMMIT': 'test_commit_version',

    'LATEXML_DB_URI': LATEXML_DB_URI,
    'CLASSIC_DB_URI': CLASSIC_DATABASE_URI,

    'LOCK_DIR': 'tests/data/locks/'
}

def get_test_config():
    return TESTING_CONFIG.copy()

@pytest.fixture
def app() -> Flask:
    app = create_web_app(get_test_config())
    # with app.app_context():
    #     drop_all()
    #     create_all()
    return app

@pytest.fixture
def app_client(app: Flask):
    with app.app_context():
        yield app.test_client()