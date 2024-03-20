from typing import List
import json

from flask import current_app

from ...domain.conversion import ConversionPayload, DocumentConversionPayload
from ...services.db import get_license_for_paper, get_license_for_submission

def generate_metadata (missing_packages: List[str], payload: ConversionPayload):
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