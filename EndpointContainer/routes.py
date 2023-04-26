"""HTTPS routes for the Flask app"""
import logging
from functools import wraps
from typing import Any, Callable, Optional
import os
import datetime
import config
from util import get_file, untar, inject_base_tag
from bs4 import BeautifulSoup, Tag
import google.cloud.logging
from google.cloud import storage
import google.auth
from google.auth.transport import requests
from authorize import authorize_user_for_submission, submission_published
from arxiv_auth.domain import Session
from flask import request, Blueprint, jsonify, render_template, current_app
from flask_cors import cross_origin

lclient = google.cloud.logging.Client()
lclient.setup_logging()
blueprint = Blueprint('routes', __name__, '')

def _get_google_auth () -> tuple[google.auth.credentials.Credentials, str, storage.Client]:
    credentials, project_id = google.auth.default()
    return (credentials, project_id, storage.Client(credentials=credentials))

def _get_auth(req) -> Optional[Session]:
    logging.info(f"request: {'None' if request is None else 'Not None'}")
    logging.info(f"hasattr(request, 'auth'): {'True' if hasattr(request, 'auth') else 'False'}")
    if request and hasattr(request, 'auth') and request.auth:
        return req.auth
    else:
        return None

def _get_url(blob_name) -> str:
    credentials, _, client = _get_google_auth()
    grequest = requests.Request()
    credentials.refresh(grequest)
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
                return jsonify ({"message": "You don't have permission to view this resource"}), 404 # do make_response
        except Exception as e:
            logging.info(str(e))
            logging.info("user denied")
            return jsonify ({"message": "You don't have permission to view this resource"}), 404 # do make_response
    return wrapper

@blueprint.route('/download', methods=['GET'])
@cross_origin(supports_credentials=True)
@authorize_for_submission
def download ():
    logging.info("Logging works in routes.py file")
    _, _, client = _get_google_auth()
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
    inject_base_tag(source, f"/templates/{blob_name.replace('.', '-')}/html/") 
    # This corrects the paths for static assets in the html
    return render_template("html_template.html", html=source)

# add exception handling
@blueprint.route('/upload', methods=['POST'])
@cross_origin(supports_credentials=True)
@authorize_for_submission
def upload ():
    # See test_signed_upload.txt for usage
    # Needs to be sent to XML endpoint in
    return jsonify({"url": _get_url(request.args.get('submission_id'))}), 200

@blueprint.route('/poll_submission', methods=['GET', 'OPTIONS'])
@cross_origin(supports_credentials=True)
@authorize_for_submission
def poll ():
    logging.info(f"CHECKING FOR AUTH IN POLL: {hasattr(request, 'auth')}")
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
        