"""Config that specifies output bucket name for uploading converted articles"""

IN_BUCKET_ARXIV_ID = 'latexml_arxiv_id_source'
OUT_BUCKET_ARXIV_ID = 'latexml_arxiv_id_converted'
OUT_BUCKET_SUB_ID = 'latexml_submission_converted'

CLASSIC_DATABASE_URI = 'sqlite:///:memory:'

QA_BUCKET_SUB = 'latexml_qa_sub'
QA_BUCKET_DOC = 'latexml_qa_doc'

LATEXML_COMMIT = 'test_commit_version'

LATEXML_DB_URI = 'sqlite:///:memory:?cache=latexml'
SQLALCHEMY_DATABASE_URI = CLASSIC_DATABASE_URI
SQLALCHEMY_BINDS = { 'latexml': LATEXML_DB_URI }

LOCK_DIR = '/arxiv/locks'