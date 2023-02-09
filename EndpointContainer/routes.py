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

from arxiv_auth.domain import Session

blueprint = Blueprint('routes', __name__, '')
credentials, project_id = google.auth.default()


def _get_auth(req) -> Optional[Session]:
    if request and hasattr(request, 'auth') and request.auth:
        return req.auth
    else:
        return None


def authorize_for_submission(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        auth = _get_auth(request)
        if (auth and request.auth.user and ('submission_id' in request.form)
            and authorize_user_for_submission(request.auth.user.user_id, request.form['submission_id'])):
            return func(*args, **kwargs)

        return jsonify ({"message": "You don't have permission to view this resource"}), 403 # do make_response
    return wrapper


@blueprint.route('/download', methods=['GET'])
@authorize_for_submission
def download (request):
    # add conversion completion verification here or in client side on button
    tar = get_file()
    source = untar(tar)
    return render_template(f"{request.form['submission_id']}.html")


@blueprint.route('/upload', methods=['POST'])
@authorize_for_submission
def upload ():

    r = requests.Request()
    credentials.refresh(r)

    bucket_name = 'latexml_submission_source'
    # blob_name = request.auth.user + "_submission"
    blob_name = 'testuser_submission'  # TODO This is just a test value

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
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

    # See test_signed_upload.txt for usage
    # Needs to be sent to XML endpoint in 
    return jsonify({"url": url}), 200

    # add exception handling
