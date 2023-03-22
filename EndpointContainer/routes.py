from flask import request, Blueprint, jsonify, render_template, current_app

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

from bs4 import BeautifulSoup

lclient = google.cloud.logging.Client()
lclient.setup_logging()

from arxiv_auth.domain import Session


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

    # blob_name = req.form['submission_id']
    # blob_name = 'testuser_submission'  # TODO This is just a test value

    bucket = client.bucket(current_app.config['SOURCE_BUCKET'])
    blob = bucket.blob(blob_name)
    
    # """Generates a v4 signed URL for uploading a blob using HTTP PUT.

    # Note that this method requires a service account key file. You can not use
    # this if you are using Application Default Credentials from Google Compute
    # Engine or from the Google Cloud SDK.
    # """

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

# TODO: Add error handling
def _inject_base_tag (html_path, base_path):
    list_files('templates')
    with open(f'/source/templates/{html_path}', 'r+') as html:
        soup = BeautifulSoup(html.read(), 'html.parser')
        logging.info(str(soup))
        base = soup.new_tag('base')
        base['href'] = base_path
        soup.find('head').append(base)
        html.seek(0)
        html.write(str(soup))


def authorize_for_submission(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        if request and 'submission_id' in request.args and submission_published(request.args.get('submission_id')):
            return func(*args, **kwargs)
        auth = _get_auth(request)
        if (auth and auth.user and ('submission_id' in request.args)
            and authorize_user_for_submission(auth.user.user_id, request.args.get('submission_id'))):
            return func(*args, **kwargs)
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
#@authorize_for_submission
def download ():
    credentials, _, client = _get_google_auth()
    blob_name = request.args.get('submission_id')
    # blob_name = 'testuser_submission'  # TODO This is just a test value
    # add conversion completion verification here or in client side on button
    try:
        tar = get_file(current_app.config['CONVERTED_BUCKET'], blob_name, client)
        source = untar(tar, blob_name)
    except:
        return {'status': False}, 404
    # list_files(".")
    _inject_base_tag(source, f"/templates/{blob_name.replace('.', '-')}/html/") # This corrects the paths for static assets in the html
    return render_template("html_template.html", html=source)
    #return render_template(f"{request.form['submission_id']}.html")


@blueprint.route('/upload', methods=['POST'])
#@authorize_for_submission
def upload ():
    print ('made it to upload')
    # r = requests.Request()
    # credentials, _, client = _get_google_auth()


    # See test_signed_upload.txt for usage
    # Needs to be sent to XML endpoint in 
    return jsonify({"url": _get_url(request.args.get('submission_id'))}), 200

    # add exception handling

@blueprint.route('/poll_submission', methods=['GET'])
#@authorize_for_submission
def poll ():
    credentials, _, client = _get_google_auth()
    submission_id = request.args.get('submission_id')
    if submission_id and \
        client.bucket(current_app.config['CONVERTED_BUCKET']) \
        .blob(submission_id).exists():
        return {'exists': True}, 200
    return {'exists': False}, 200
        