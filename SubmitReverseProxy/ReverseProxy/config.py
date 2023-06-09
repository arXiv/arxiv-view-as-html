"""Config that specifies arxiv database address through GCP, html template directory, and 
bucket names for article source and converted articles"""
import os

CLASSIC_SESSION_HASH = os.environ.get('CLASSIC_SESSION_HASH')

CLASSIC_DATABASE_URI = os.environ.get('CLASSIC_DATABASE_URI')

CLASSIC_COOKIE_NAME = 'tapir_session'
SESSION_DURATION = 36000

# ARXIV_AUTH_DEBUG = 1
AUTH_UPDATED_SESSION_REF = True

"""If not set, legacy database integrations will not be available."""

# LEGACY DB URI
SQLALCHEMY_DATABASE_URI = CLASSIC_DATABASE_URI

#LATEXML DB URI
LATEXML_DB_URI = os.environ.get('LATEXML_DB_URI')

# Response bucket
CONVERTED_BUCKET_SUB_ID = 'latexml_submission_converted'

SITES_DIR = '/source/ReverseProxy/sites/'
TARS_DIR = '/source/ReverseProxy/downloads/'

