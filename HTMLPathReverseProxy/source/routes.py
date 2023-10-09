from typing import Tuple, Optional, Callable, Any
from functools import wraps
import logging
import os

from flask import Blueprint, Request, \
    request, current_app, \
    send_from_directory, g, \
    redirect
# from flask_cors import cross_origin
from werkzeug.exceptions import BadRequest

from google.cloud.storage import Client
import google.auth
from google.auth.credentials import Credentials
from google.auth.transport import requests

from .util import untar, clean_up

blueprint = Blueprint('routes', __name__, '')

def _get_google_auth () -> Tuple[Credentials, str, Client]:
    credentials, project_id = google.auth.default()
    return (credentials, project_id, Client(credentials=credentials))

@blueprint.route('/html/<arxiv_id>', methods=['GET'])
def get (arxiv_id: str):
    if arxiv_id.endswith('.html'):
        return redirect(f'/html/{arxiv_id.split(".html")[0]}')
    BUCKET = current_app.config['CONVERTED_BUCKET_ARXIV_ID']
    TARS_DIR = current_app.config['TARS_DIR']

    _, _, storage_client = _get_google_auth()
    bucket = storage_client.get_bucket(BUCKET)
    blob = bucket.blob(f'{arxiv_id}.tar.gz')

    blob.download_to_filename(f'{TARS_DIR}{arxiv_id}')

    logging.info(f'Successfully downloaded to {TARS_DIR}{arxiv_id}')

    abs_path = untar(arxiv_id)
    dir = os.path.relpath(abs_path, current_app.root_path)

    logging.info(f'Successfully untarred to {abs_path}')
    
    return send_from_directory (dir, f'{arxiv_id}.html')

@blueprint.route('/html/<arxiv_id>/<path:path>', methods=['GET'])
# @cross_origin(supports_credentials=True)
def get_static (arxiv_id: str, path: str):
    SITES_DIR = current_app.config['SITES_DIR']

    dir = os.path.join(
        os.path.relpath(SITES_DIR, current_app.root_path),
        arxiv_id
    )

    return send_from_directory (dir, path)


@blueprint.app_errorhandler(BadRequest)
# @cross_origin(supports_credentials=True)
def handle_bad_request(e):
    # TODO: 404 Page for submissions?
    logging.warning(f'Error: {e}')
    return 'Internal Server Error', 500

@blueprint.app_errorhandler(500)
# @cross_origin(supports_credentials=True)
def handle_500(e):
    # TODO: 404 Page for submissions?
    logging.warning(f'Error: {e}')
    return 'Internal Server Error', 500

@blueprint.app_errorhandler(404)
# @cross_origin(supports_credentials=True)
def handle_404(e):
    # TODO: 404 Page for submissions?
    logging.warning(f'Error: {e}')
    return 'This page does not exist', 404
