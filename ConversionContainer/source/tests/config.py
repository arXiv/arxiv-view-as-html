"""Config that specifies output bucket name for uploading converted articles"""

IN_BUCKET_ARXIV_ID = 'latexml_arxiv_id_source'
OUT_BUCKET_ARXIV_ID = 'latexml_arxiv_id_converted'
OUT_BUCKET_SUB_ID = 'latexml_submission_converted'

QA_BUCKET_SUB = 'latexml_qa_sub'
QA_BUCKET_DOC = 'latexml_qa_doc'


LATEXML_COMMIT = 'test_commit_version'

LATEXML_DB_URI = 'sqlite://'
SQLALCHEMY_DATABASE_URI = LATEXML_DB_URI

LOCK_DIR = '/arxiv/locks'