"""Config that specifies output bucket name for uploading converted articles"""

import os

CLASSIC_DATABASE_URI = os.environ.get('CLASSIC_DATABASE_URI')

OUT_BUCKET_ARXIV_ID = os.environ['DOCUMENT_CONVERTED_BUCKET'] # Startup failure on miss
IN_BUCKET_SUB_ID = os.environ['SUBMISSION_SOURCE_BUCKET'] # Startup failure on miss
OUT_BUCKET_SUB_ID = os.environ['SUBMISSION_CONVERTED_BUCKET'] # Startup failure on miss

QA_BUCKET_SUB = os.environ['QA_BUCKET_SUB'] # Startup failure on miss
QA_BUCKET_DOC = os.environ['QA_BUCKET_DOC']

LATEXML_COMMIT = os.environ['LATEXML_COMMIT']

LATEXML_DB_URI = os.environ['LATEXML_DB_URI']
LATEXML_URL_BASE = os.environ['LATEXML_URL_BASE']
VIEW_SUB_BASE = os.environ['VIEW_SUB_BASE']
VIEW_DOC_BASE = os.environ['VIEW_DOC_BASE']

SQLALCHEMY_DATABASE_URI = CLASSIC_DATABASE_URI
SQLALCHEMY_BINDS = { 'latexml': LATEXML_DB_URI }

LOCK_DIR = '/arxiv/locks'