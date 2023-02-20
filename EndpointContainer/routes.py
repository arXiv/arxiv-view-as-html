from flask import request, Blueprint, jsonify, render_template

from functools import wraps

from typing import Any, Callable, Optional

import config
from util import *
import datetime
from google.cloud import storage
import google.auth
from google.auth.transport import requests
from authorize import authorize_user_for_submission
import logging

import google.cloud.logging
lclient = google.cloud.logging.Client()
lclient.setup_logging()

from arxiv_auth.domain import Session

blueprint = Blueprint('routes', __name__, '')

def _get_google_auth () -> tuple[google.auth.credentials.Credentials, str, storage.Client]:
    return *google.auth.default(), storage.Client()

def _get_auth(req) -> Optional[Session]:
    if request and hasattr(request, 'auth') and request.auth:
        return req.auth
    else:
        return None

def _get_url(req, credentials, client) -> str:

    credentials.refresh(request)

    bucket_name = 'latexml_submission_source'
    # blob_name = request.auth.user + "_submission"
    blob_name = 'testuser_submission'  # TODO This is just a test value

    bucket = client.bucket(bucket_name)
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


def authorize_for_submission(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        auth = _get_auth(request)
        if (auth and auth.user and ('submission_id' in request.form)
            and authorize_user_for_submission(auth.user.user_id, request.form['submission_id'])):
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
# @authorize_for_submission
def download ():
    credentials, _, client = _get_google_auth()
    bucket_name = 'latexml_submission_converted'
    # blob_name = request.auth.user + "_submission"
    blob_name = 'testuser_submission'  # TODO This is just a test value
    # add conversion completion verification here or in client side on button
    tar = get_file(bucket_name, blob_name, client)
    source = untar(tar)
    # list_files(".")
    return render_template("html/testuser_submission.html")
    #return render_template(f"{request.form['submission_id']}.html")


@blueprint.route('/upload', methods=['POST'])
@authorize_for_submission
def upload ():
    print ('made it to upload')
    #r = requests.Request()
    credentials, _, client = _get_google_auth()


    # See test_signed_upload.txt for usage
    # Needs to be sent to XML endpoint in 
    return jsonify({"url": _get_url(request, credentials, client)}), 200

    # add exception handling
