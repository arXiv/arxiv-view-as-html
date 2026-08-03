"""Config that specifies arxiv database address through GCP, html template directory, and 
bucket names for article source and converted articles"""
import os

CLASSIC_SESSION_HASH = os.environ.get('CLASSIC_SESSION_HASH')

CLASSIC_DATABASE_URI = os.environ.get('CLASSIC_DATABASE_URI')

CLASSIC_COOKIE_NAME = 'tapir_session'
SESSION_DURATION = 36000

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

# pub/sub
PROJECT_ID = os.environ.get('PROJECT_ID', 'arxiv-development')
BUILD_HTML_TOPIC = os.environ.get('BUILD_HTML_TOPIC', 'html-direct-convert')
REPROCESS_SUBMISSION_TOPIC = os.environ.get('REPROCESS_SUBMISSION_TOPIC', 'html-reprocess-submission')

SITES_DIR = '/source/ReverseProxy/sites/'
TARS_DIR = '/source/ReverseProxy/downloads/'

# The shared `base/footer.html` is vendored from arxiv-base master (see dockerfiles/), but the
# `arxiv-base` that `arxiv-auth` pins is old enough that its external URL map still sends these
# to arxiv.org. Those still reach the reader, though only via a 301 to info.arxiv.org and then
# a 404 page whose JS appends the `.html`. Master's table links straight at the final page, so
# take it from there (arxiv/base/config.py URLS, with HELP_SERVER resolved) and render the
# footer arxiv-browse renders. Only the endpoints that footer actually uses are listed.
HELP_SERVER = 'info.arxiv.org'
URLS = [
    ('a11y', '/help/web_accessibility.html', HELP_SERVER),
    ('about', '/about', HELP_SERVER),
    ('acknowledgment', '/about/ourmembers.html', HELP_SERVER),
    ('contact', '/help/contact.html', HELP_SERVER),
    ('copyright', '/help/license/index.html', HELP_SERVER),
    ('help', '/help', HELP_SERVER),
    ('privacy_policy', '/help/policies/privacy_policy.html', HELP_SERVER),
    ('subscribe', '/help/subscribe', HELP_SERVER),
]
