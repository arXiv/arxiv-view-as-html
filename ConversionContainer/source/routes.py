"""HTTPS routes for the Flask app"""
from typing import Tuple, Dict
from datetime import datetime
import os
from threading import Thread
import logging

import flask
from flask import Blueprint, request, jsonify, \
    current_app, Response

from .convert import process
from .publish import publish


# FlaskThread pushes the Flask applcation context
class FlaskThread(Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = current_app._get_current_object()

    def run(self):
        with self.app.app_context():
            super().run()

blueprint = Blueprint('routes', __name__)


# Unwraps payload and only starts processing if it is 
# the desired format and a .tar.gz
def _unwrap_payload (payload: Dict[str, str]) -> Tuple[str, str]:
    if payload['name'].endswith('.gz'):
        id = payload['name'].split('/')[1].replace('.tar.gz', '')
        return id, payload['name'], payload['bucket']
    raise ValueError ('Received extraneous file')


# The post request from the eventarc trigger that queries this route will come in this format:
# https://github.com/googleapis/google-cloudevents/blob/main/proto/google/events/cloud/storage/v1/data.proto
@blueprint.route('/process', methods=['POST'])
def process_route () -> Response:
    """
    Takes in the eventarc trigger payload and creates a thread
    to perform the latexml conversion on the blob specified
    in the payload.

    Returns
    -------
    Response
        Returns a 202 response with no payload
    """
    try:
        id, blob, bucket = _unwrap_payload(request.json)
    except Exception as e:
        logging.info(f'Discarded request with {e}')
        return '', 403
    logging.info(f'Begin processing for {blob} from {bucket}')
    thread = FlaskThread(target=process, args=(id, blob, bucket))
    thread.start()
    return '', 202

@blueprint.route('/publish', methods=['POST'])
def publish_route () -> Response:
    logging.info(request.json)
    thread = FlaskThread(target=publish, args=(request.json,))
    thread.start()
    return '', 202

@blueprint.route('/health', methods=['GET'])
def health() -> tuple[flask.Response, int]:
    """
    Returns the latexml statuses and current time.

    Returns
    -------
    tuple[flask.Response, int]
        List of current cloud run tasks and the current time.
    """
    data = {
        "time": datetime.now(),
        "CLOUD_RUN_TASK_INDEX": list(os.environ.items())
    }
    print (data)
    return jsonify(data), 200
    