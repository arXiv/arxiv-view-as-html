"""HTTPS routes for the Flask app."""

import json
import logging
from base64 import b64decode
from typing import Any, Dict

from arxiv.identifier import Identifier
from flask import Blueprint, Response, current_app, request

# from ..convert.batch_convert import batch_process
# from ..convert.single_convert import single_convert, reconvert_submission
# from ..publish import publish
from ..domain.conversion import DocumentConversionPayload, SubmissionConversionPayload
from ..domain.publish import PublishPayload
from ..processes.convert import process
from ..processes.publish import publish
from ..services.db import get_document_is_latest, get_document_is_single_file

logger = logging.getLogger()

blueprint = Blueprint("routes", __name__)


def _unwrap_pubsub_payload(payload: dict[str, Any]) -> Any:
    return json.loads(b64decode(payload["message"]["data"]).decode("utf-8"))


def unwrap_submission_conversion_payload(payload: dict[str, Any]) -> SubmissionConversionPayload:
    data = _unwrap_pubsub_payload(payload)
    return SubmissionConversionPayload(identifier=int(data["submission_id"]), single_file=data.get("single_file"))


def unwrap_document_conversion_payload(payload: dict[str, str]) -> DocumentConversionPayload:
    data = _unwrap_pubsub_payload(payload)
    identifier = Identifier(f"{data['paper_id']}v{data['version']}")
    return DocumentConversionPayload(
        identifier=identifier,
        single_file=get_document_is_single_file(identifier),
        is_latest=get_document_is_latest(identifier),
    )


def unwrap_publish_payload(payload: dict[str, str]) -> PublishPayload:
    data = _unwrap_pubsub_payload(payload)
    return PublishPayload(
        submission_id=data["submission_id"], paper_id=Identifier(f"{data['paper_id']}v{data['version']}")
    )


# The post request from the eventarc trigger that queries this route will come in this format:
# https://github.com/googleapis/google-cloudevents/blob/main/proto/google/events/cloud/storage/v1/data.proto
@blueprint.route("/process", methods=["POST"])
def process_route() -> Response:
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
        sub_conversion_payload = unwrap_submission_conversion_payload(request.json)  # type: ignore
    except Exception:
        try:
            logger.warn(f"PROCESS: Failed to parse payload for {request.json}")
        except Exception:
            logger.warn("PROCESS: Failed to process due to malformed payload")
        return Response(status=202)
    # thread = FlaskThread(target=process, args=(sub_conversion_payload,)) # This requires cpu allocation always on in cloud run
    # thread.start()
    process(sub_conversion_payload)
    return Response(status=200)


@blueprint.route("/process-full-corpus", methods=["POST"])
def process_full_corpus() -> Response:
    if not current_app.config["IS_FULL_CORPUS_CONVERT_MACHINE"]:
        return Response(status=404)
    try:
        data = json.loads(request.get_json())
        doc_conversion_payload = DocumentConversionPayload(
            identifier=Identifier(f'{data["paper_id"]}v{data["version"]}'),
            single_file=data["single_file"],
            is_latest=data["is_latest"],
        )
    except Exception as e:
        print(f"PROCESS_FULL_CORPUS: Failed to parse payload for {request.get_json(silent=True)} with {e}")
        logger.warn(
            f"PROCESS_FULL_CORPUS: Failed to parse payload for {request.get_json(silent=True)} with {e}", exc_info=True
        )
        return Response(status=202)
    print(doc_conversion_payload)
    process(doc_conversion_payload)
    return Response(status=200)


# @blueprint.route('/batch-convert', methods=['POST'])
# def batch_convert_route () -> Response:
#     batch_process(*_unwrap_batch_conversion_payload(request.json))
#     return '', 200


@blueprint.route("/single-convert", methods=["POST"])
def single_convert_route() -> Response:
    try:
        doc_conversion_payload = unwrap_document_conversion_payload(request.get_json())
    except Exception:
        try:
            logger.warn(f"PROCESS: Failed to parse payload for {request.json}")
        except Exception:
            logger.warn("PROCESS: Failed to process due to malformed payload")
        return Response(status=202)
    process(doc_conversion_payload)
    return Response(status=200)


# @blueprint.route('/reconvert-submission', methods=['POST'])
# def reprocess_submission () -> Response:
#     thread = FlaskThread(target=reconvert_submission, args=_unwrap_reconvert_sub_payload(request.json))
#     thread.start()
#     return '', 200


@blueprint.route("/publish", methods=["POST"])
def publish_route() -> Response:
    try:
        publish_payload = unwrap_publish_payload(request.json)  # type: ignore
    except Exception:
        try:
            logger.warn(f"PUBLISH: Failed to parse payload for {request.json}")
        except Exception:
            logger.warn("PUBLISH: Failed to publish due to malformed payload")
        return Response(status=202)
    publish(publish_payload)
    return Response(status=202)
