"""Config that specifies output bucket name for uploading converted articles"""

import os

IN_BUCKET_ARXIV_ID = os.environ['DOCUMENT_SOURCE_BUCKET'] # Startup failure on miss
OUT_BUCKET_ARXIV_ID = os.environ['DOCUMENT_CONVERTED_BUCKET'] # Startup failure on miss
OUT_BUCKET_SUB_ID = os.environ['SUBMISSION_SOURCE_BUCKET'] # Startup failure on miss
QA_BUCKET_NAME = os.environ['QA_BUCKET'] # Startup failure on miss

LATEXML_COMMIT = os.environ['LATEXML_COMMIT']

LATEXML_DB_URI = os.environ['LATEXML_DB_URI']
SQLALCHEMY_DATABASE_URI = LATEXML_DB_URI

LOCK_DIR = '/arxiv/locks'