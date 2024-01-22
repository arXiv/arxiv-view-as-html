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

# LaTeXML DB URI
SQLALCHEMY_BINDS = { "latexml": os.environ.get('LATEXML_DB_URI') }
#LATEXML DB URI
LATEXML_DB_URI = os.environ.get('LATEXML_DB_URI')

# buckets
CONVERTED_BUCKET_ARXIV_ID = os.environ.get('LATEXML_ARXIV_ID_CONVERSIONS')
CONVERTED_BUCKET_SUB_ID = os.environ.get('LATEXML_SUBMISSION_CONVERSIONS')
CLASSIC_HTML_BUCKET = os.environ.get('CLASSIC_HTML_BUCKET')

SITES_DIR = '/source/ReverseProxy/sites/'
TARS_DIR = '/source/ReverseProxy/downloads/'

VIEW_SUB_BASE = os.environ.get('VIEW_SUB_BASE')
