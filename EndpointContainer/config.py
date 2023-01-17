import os

CLASSIC_SESSION_HASH = 'classic_session_hash'

CLASSIC_DATABASE_URI = os.environ.get('CLASSIC_DATABASE_URI')
"""If not set, legacy database integrations will not be available."""

SQLALCHEMY_DATABASE_URI = CLASSIC_DATABASE_URI

STATIC_FOLDER = '/static'
TEMPLATE_FOLDER = '/static'