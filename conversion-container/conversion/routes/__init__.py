"""HTTPS routes for the Flask app"""
from typing import Any, Dict
from datetime import datetime
import os
import logging
import json
from base64 import b64decode

import flask
from flask import Blueprint, request, jsonify, \
    current_app, Response

from arxiv.identifier import Identifier

from ..processes.convert import process
from ..processes.publish import publish
# from ..convert.batch_convert import batch_process
# from ..convert.single_convert import single_convert, reconvert_submission
# from ..publish import publish
from ..domain.conversion import SubmissionConversionPayload, \
    DocumentConversionPayload
from ..domain.publish import PublishPayload

from .flask_thread import FlaskThread

logger = logging.getLogger()

blueprint = Blueprint('routes', __name__)

def _unwrap_pubsub_payload (payload: Dict[str, str]) -> Any:
    return json.loads(b64decode(payload['message']['data']).decode('utf-8'))

def unwrap_submission_conversion_payload (payload: Dict[str, str]) -> SubmissionConversionPayload:
    data = _unwrap_pubsub_payload(payload)
    return SubmissionConversionPayload(
        identifier=int(data['submission_id']),
        single_file=data['single_file']
    )

def unwrap_document_conversion_payload (payload: Dict[str, str]) -> DocumentConversionPayload:
    data = _unwrap_pubsub_payload(payload)
    return DocumentConversionPayload(
        identifier=Identifier(f"{data['paper_id']}v{data['version']}"),
        single_file=data['single_file']
    )

def unwrap_publish_payload (payload: Dict[str, str]) -> PublishPayload:
    data = _unwrap_pubsub_payload(payload)
    return PublishPayload(
        submission_id=data['submission_id'],
        paper_id = Identifier(f"{data['paper_id']}v{data['version']}")
    )

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
        sub_conversion_payload = unwrap_submission_conversion_payload(request.json)
    except Exception as e:
        try:
            logger.warn(f'PROCESS: Failed to parse payload for {request.json}')
        except:
            logger.warn(f'PROCESS: Failed to process due to malformed payload')
        return '', 202
    # thread = FlaskThread(target=process, args=(sub_conversion_payload,)) # This requires cpu allocation always on in cloud run
    # thread.start()
    process (sub_conversion_payload)
    return '', 200

# @blueprint.route('/batch-convert', methods=['POST'])
# def batch_convert_route () -> Response:
#     batch_process(*_unwrap_batch_conversion_payload(request.json))
#     return '', 200

# @blueprint.route('/single-convert', methods=['POST'])
# def single_convert_route () -> Response:
#     thread = FlaskThread(target=single_convert, args=_unwrap_single_conversion_payload(request.json))
#     thread.start()
#     return '', 200

# @blueprint.route('/reconvert-submission', methods=['POST'])
# def reprocess_submission () -> Response:
#     thread = FlaskThread(target=reconvert_submission, args=_unwrap_reconvert_sub_payload(request.json))
#     thread.start()
#     return '', 200

@blueprint.route('/publish', methods=['POST'])
def publish_route () -> Response:
    try:
        publish_payload = unwrap_publish_payload(request.json)
    except Exception as e:
        try:
            logger.warn(f'PUBLISH: Failed to parse payload for {request.json}')
        except:
            logger.warn(f'PUBLISH: Failed to publish due to malformed payload')
        return '', 202
    publish(publish_payload)
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
    return jsonify(data), 200
    