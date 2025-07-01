import json
from typing import List

from flask import current_app

from ...domain.conversion import ConversionPayload, DocumentConversionPayload, SubmissionConversionPayload
from ...domain.publish import PublishPayload
from ...services.db import (
    get_license_for_paper,
    get_license_for_submission,
    get_submission_timestamp_from_arxiv_identifier,
    get_version_primary_category,
)


def generate_metadata_convert(payload: ConversionPayload, missing_packages: List[str]) -> str:
    if isinstance(payload, DocumentConversionPayload):
        return json.dumps(
            {
                "missing_packages": missing_packages or None,
                "license": get_license_for_paper(payload.identifier),
                "base_url": f'{current_app.config["VIEW_DOC_BASE"]}/html/{payload.identifier.idv}',
                "primary_category": get_version_primary_category(payload.identifier),
                "submission_timestamp": get_submission_timestamp_from_arxiv_identifier(payload.identifier),
                "id": payload.identifier.idv,
            }
        )
    elif isinstance(payload, SubmissionConversionPayload):  # Need to do this to appease mypy
        return json.dumps(
            {
                "missing_packages": missing_packages or None,
                "license": get_license_for_submission(payload.identifier),
                "base_url": f'{current_app.config["VIEW_SUB_BASE"]}/html/submission/{payload.identifier}/view',
            }
        )
    else:
        raise ValueError(f"Unknown payload type: {type(payload)}")


def generate_metadata_publish(payload: PublishPayload, existing_metadata: str) -> str:
    metadata = json.loads(existing_metadata)
    metadata["base_url"] = f'{current_app.config["VIEW_DOC_BASE"]}/html/{payload.paper_id.idv}'
    metadata["primary_category"] = get_version_primary_category(payload.paper_id)
    metadata["submission_timestamp"] = get_submission_timestamp_from_arxiv_identifier(payload.paper_id)
    metadata["id"] = payload.paper_id.idv
    return json.dumps(metadata)
