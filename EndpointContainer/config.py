"""Config that specifies arxiv database address through GCP, html template directory, and 
bucket names for article source and converted articles"""
import os

CLASSIC_SESSION_HASH = os.environ.get('CLASSIC_SESSION_HASH')

CLASSIC_DATABASE_URI = os.environ.get('CLASSIC_DATABASE_URI')

CLASSIC_COOKIE_NAME = 'tapir_session'
SESSION_DURATION = 36000

ARXIV_AUTH_DEBUG = 1
AUTH_UPDATED_SESSION_REF = True

"""If not set, legacy database integrations will not be available."""

SQLALCHEMY_DATABASE_URI = CLASSIC_DATABASE_URI

STATIC_FOLDER = '/static'
# STATIC_FOLDER = '/templates'
TEMPLATE_FOLDER = '/templates'

SOURCE_BUCKET = 'latexml_submission_source'
CONVERTED_BUCKET_SUB_ID = 'latexml_submission_converted'
CONVERTED_BUCKET_ARXIV_ID = None
QA_BUCKET_NAME = "latexml_qa"
