from typing import Tuple, Optional, Callable, Any
from functools import wraps
import logging
import os

from flask import Blueprint, Request, \
    request, current_app, send_from_directory
from flask_cors import cross_origin
from werkzeug.exceptions import BadRequest

from google.cloud.storage import Client
import google.auth
from google.auth.credentials import Credentials
from google.auth.transport import requests

from .authorize import authorize_user_for_submission
from .util import untar, clean_up
from .exceptions import AuthError

blueprint = Blueprint('routes', __name__, '')

def _get_google_auth () -> Tuple[Credentials, str, Client]:
    credentials, project_id = google.auth.default()
    return (credentials, project_id, Client(credentials=credentials))

def _get_arxiv_user_id (req: Request) -> int:
    if hasattr(request, 'auth') and request.auth is not None and \
        hasattr(request.auth, 'user') and \
            request.auth.user is not None and \
            hasattr(request.auth.user, 'user_id') and \
            type(request.auth.user.user_id) == int:
        return req.auth.user.user_id
    else:
        raise AuthError
    
@blueprint.route('/submission/<int:submission_id>', methods=['GET'])
@cross_origin(supports_credentials=True)
def get (submission_id: int):
    user_id = _get_arxiv_user_id(request)
    authorize_user_for_submission(user_id, submission_id)

    BUCKET = current_app.config['CONVERTED_BUCKET_SUB_ID']
    TARS_DIR = current_app.config['TARS_DIR']

    _, _, storage_client = _get_google_auth()
    bucket = storage_client.get_bucket(BUCKET)
    blob = bucket.blob(f'{submission_id}.tar.gz')


    blob.download_to_filename(f'{TARS_DIR}{submission_id}')

    logging.info(f'Successfully downloaded to {TARS_DIR}{submission_id}')

    abs_path = untar(submission_id)
    dir = os.path.relpath(abs_path, current_app.root_path)

    logging.info(f'Successfully untarred to {abs_path}')
    
    return send_from_directory (dir, f'{submission_id}.html')

@blueprint.route('/submission/<int:submission_id>/<path:path>', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_static (submission_id: int, path: str):
    SITES_DIR = current_app.config['SITES_DIR']

    dir = os.path.join(
        os.path.relpath(SITES_DIR, current_app.root_path),
        str(submission_id)
    )

    return send_from_directory (dir, path)


@blueprint.errorhandler(BadRequest)
def handle_bad_request(e):
    # TODO: 404 Page for submissions?
    logging.warning(f'Error: {e}')
    return 'This page does not exist', 404