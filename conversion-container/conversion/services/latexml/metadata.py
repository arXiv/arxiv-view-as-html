from typing import List, Dict, Any
import json

from flask import current_app

from ...domain.publish import PublishPayload
from ...domain.conversion import ConversionPayload, DocumentConversionPayload
from ...services.db import (
    get_license_for_paper, 
    get_license_for_submission,
    get_version_primary_category,
    get_submission_timestamp_from_arxiv_identifier
)

def generate_metadata_convert (payload: ConversionPayload, missing_packages: List[str]) -> str:
    if isinstance(payload, DocumentConversionPayload):
        license = get_license_for_paper(payload.identifier)
        base_url = f'{current_app.config["VIEW_DOC_BASE"]}/html/{payload.identifier.idv}'
    else:
        license = get_license_for_submission(payload.identifier)
        base_url = f'{current_app.config["VIEW_SUB_BASE"]}/html/submission/{payload.identifier}/view'
    return json.dumps({
        'missing_packages': missing_packages,
        'license': license,
        'base_url': base_url
    })

def generate_metadata_publish (payload: PublishPayload, existing_metadata: str) -> str:
    metadata = json.loads(existing_metadata)
    metadata['base_url']= f'{current_app.config["VIEW_DOC_BASE"]}/html/{payload.paper_id.idv}'
    metadata['primary_category'] = get_version_primary_category(payload.paper_id)
    metadata['submission_timestamp'] = get_submission_timestamp_from_arxiv_identifier(payload.paper_id)
    return json.dumps(metadata)
    