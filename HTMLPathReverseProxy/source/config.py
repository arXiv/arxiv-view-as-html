"""Config that specifies html template directory, bucket names, etc."""
import os


CLASSIC_DATABASE_URI = os.environ.get('CLASSIC_DATABASE_URI')

"""If not set, legacy database integrations will not be available."""

# LEGACY DB URI
SQLALCHEMY_DATABASE_URI = CLASSIC_DATABASE_URI

# LaTeXML DB URI
SQLALCHEMY_BINDS = { "latexml": os.environ.get('LATEXML_DB_URI') }
#LATEXML DB URI
LATEXML_DB_URI = os.environ.get('LATEXML_DB_URI')

# Response bucket
CONVERTED_BUCKET_ARXIV_ID = os.environ.get('LATEXML_ARXIV_ID_CONVERSIONS')

SITES_DIR = '/source/sites/'
TARS_DIR = '/source/downloads/'

