import pytest

from source.factory import create_web_app
from source.models.util import (
    create_all,
    drop_all,
)

LATEXML_DB_URI = 'sqlite:///:memory:?cache=latexml'
CLASSIC_DATABASE_URI = 'sqlite:///:memory:'

TESTING_CONFIG = {
    'IN_BUCKET_ARXIV_ID': 'latexml_arxiv_id_source',
    'OUT_BUCKET_ARXIV_ID': 'latexml_arxiv_id_converted',
    'OUT_BUCKET_SUB_ID': 'latexml_submission_converted',

    'CLASSIC_DATABASE_URI': 'sqlite:///:memory:',

    'QA_BUCKET_SUB': 'latexml_qa_sub',
    'QA_BUCKET_DOC': 'latexml_qa_doc',

    'LATEXML_COMMIT': 'test_commit_version',

    'LATEXML_DB_URI': LATEXML_DB_URI,
    'SQLALCHEMY_DATABASE_URI': CLASSIC_DATABASE_URI,
    'SQLALCHEMY_BINDS': { 'latexml': LATEXML_DB_URI },

    'LOCK_DIR': '/arxiv/locks'
}

def get_test_config():
    return TESTING_CONFIG.copy()

@pytest.fixture
def app():
    app = create_web_app(get_test_config())
    with app.app_context():
        drop_all()
        create_all()
    return app

@pytest.fixture
def app_client(app):
    with app.app_context():
        yield app.test_client()