"""HTTPS routes for the Flask app"""
from typing import Tuple, Dict
from datetime import datetime
import os
from threading import Thread
import logging
import json
from base64 import b64decode

import flask
from flask import Blueprint, request, jsonify, \
    current_app, Response

from .convert import process
from .convert.batch_convert import batch_process
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
def _unwrap_payload (payload: Dict[str, str]) -> Tuple[str, str, str, bool]:
    if payload['name'].endswith('.gz'):
        if payload['name'].endswith('.tar.gz'):
            single_file = False
            id = payload['name'].split('/')[1].replace('.tar.gz', '')
        else:
            single_file = True
            id = payload['name'].split('/')[1].replace('.gz', '')
        return id, payload['name'], payload['bucket'], single_file
    raise ValueError ('Received extraneous file')

def _unwrap_batch_conversion_payload (payload: Dict[str, str]) -> Tuple[str, str, str]:
    data = json.loads(b64decode(payload['message']['data']).decode('utf-8'))
    return (
        data['id'],
        data['blob'],
        data['bucket']
    )

def _unwrap_single_conversion_payload (payload: Dict[str, str]) -> Tuple[str, str, str]:
    return {
        payload['id'],
        payload['blob'],
        payload['bucket']
    }

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
        id, blob, bucket, single_file = _unwrap_payload(request.json)
    except Exception as e:
        logging.info(f'Discarded request for {request.json["name"]}')
        return '', 202
    logging.info(f'Begin processing for {blob} from {bucket}')
    process(id, blob, bucket, single_file)
    return '', 200

@blueprint.route('/batch-convert', methods=['POST'])
def batch_convert_route () -> Response:
    batch_process(*_unwrap_batch_conversion_payload(request.json))
    return '', 200

@blueprint.route('/single-convert', methods=['POST'])
def single_convert_route () -> Response:
    batch_process(*_unwrap_single_conversion_payload(request.json))
    return '', 200

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
    