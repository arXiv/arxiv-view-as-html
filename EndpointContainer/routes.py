from flask import request, Blueprint, jsonify, render_template, current_app
from flask_cors import cross_origin
from functools import wraps

from typing import Any, Callable, Optional

import os
import config
from util import *
import datetime
from google.cloud import storage
import google.auth
from google.auth.transport import requests
from authorize import authorize_user_for_submission, submission_published
import logging
import google.cloud.logging
from arxiv_auth.domain import Session
from bs4 import BeautifulSoup, Tag

lclient = google.cloud.logging.Client()
lclient.setup_logging()
blueprint = Blueprint('routes', __name__, '')

def _get_google_auth () -> tuple[google.auth.credentials.Credentials, str, storage.Client]:
    credentials, project_id = google.auth.default()
    return (credentials, project_id, storage.Client(credentials=credentials))

def _get_auth(req) -> Optional[Session]:
    if request and hasattr(request, 'auth') and request.auth:
        return req.auth
    else:
        return None

def _get_url(blob_name) -> str:
    credentials, _, client = _get_google_auth()
    request = requests.Request()
    credentials.refresh(request)
    bucket = client.bucket(current_app.config['SOURCE_BUCKET'])
    blob = bucket.blob(blob_name)
    
    # """Generates a v4 signed URL for uploading a blob using HTTP PUT.
    url = blob.generate_signed_url(
        version="v4",
        # This URL is valid for 10 minutes
        expiration=datetime.timedelta(minutes=10),
        # Allow PUT requests using this URL.
        method="PUT",
        # Use updated credentials (new token for signature is created by Google every 12 hours)
        service_account_email=credentials.service_account_email,
        access_token=credentials.token,
    )

    return url

def authorize_for_submission(func: Callable) -> Callable: # This decorators needs to come before the @blueprint.route decorator
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        try:
            if request and 'submission_id' in request.args and submission_published(request.args.get('submission_id')):
                logging.info(f"Submission {request.args['submission_id']} authorized because it's already published")
                return func(*args, **kwargs)
            logging.info("Submission is not published (try)")
        except:
            logging.info(f"Submission is not published")
            # What to do if DB isn't configured?
        auth = _get_auth(request)
        try:
            if (auth and auth.user and ('submission_id' in request.args)
                and authorize_user_for_submission(auth.user.user_id, request.args.get('submission_id'))):
                logging.info(f"Submission {request.args['submission_id']} authorized for user {auth.user.user_id} because they are the submitter")
                return func(*args, **kwargs)
            else:
                logging.info(f"Auth failed: \nIs auth None: {auth is None}\nIs user None: {hasattr(auth, 'user')}")
                if hasattr(auth, 'user'):
                    logging.info(f'User Id: {auth.user.user_id}')
                return jsonify ({"message": "You don't have permission to view this resource"}), 403 # do make_response
        except:
            logging.info("user denied")
            return jsonify ({"message": "You don't have permission to view this resource"}), 403 # do make_response
    return wrapper

def list_files(startpath):
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        logging.info('{}{}/'.format(indent, os.path.basename(root)))
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            logging.info('{}{}'.format(subindent, f))

@blueprint.route('/download', methods=['GET'])
@authorize_for_submission
def download ():
    logging.info("Logging works in routes.py file")
    credentials, _, client = _get_google_auth()
    blob_name = request.args.get('arxiv_id') or request.args.get('submission_id')
    if blob_name is None:
        return {'status': False}, 404
    try:
        tar = get_file(
            current_app.config[
                'CONVERTED_BUCKET_ARXIV_ID' if request.args.get('arxiv_id')
                else 'CONVERTED_BUCKET_SUB_ID'], 
            blob_name, 
            client)
        source = untar(tar, blob_name)
    except:
        return {'status': False}, 404
    inject_base_tag(source, f"/templates/{blob_name.replace('.', '-')}/html/") # This corrects the paths for static assets in the html
    return render_template("html_template.html", html=source)

# add exception handling
@blueprint.route('/upload', methods=['POST'])
@authorize_for_submission
def upload ():
    # See test_signed_upload.txt for usage
    # Needs to be sent to XML endpoint in 
    return jsonify({"url": _get_url(request.args.get('submission_id'))}), 200

@blueprint.route('/poll_submission', methods=['GET'])
@authorize_for_submission
@cross_origin()
def poll ():
    try:
        _, _, client = _get_google_auth()
    except:
        logging.critical ("Failed to get GCP credentials")
        return {'exists': False}, 500
    arxiv_id = request.args.get('arxiv_id')
    if arxiv_id and \
        client.bucket(current_app.config['CONVERTED_BUCKET_ARXIV_ID']) \
        .blob(arxiv_id).exists():
            return {'exists': True}, 200
    submission_id = request.args.get('submission_id')
    if submission_id and \
        client.bucket(current_app.config['CONVERTED_BUCKET_SUB_ID']) \
        .blob(submission_id).exists():
            return {'exists': True}, 200
    return {'exists': False}, 200
        