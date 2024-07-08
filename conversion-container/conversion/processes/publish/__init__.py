from typing import Dict, Tuple
import logging
import shutil
from base64 import b64decode
import json
from flask import current_app


from arxiv.identifier import Identifier
from arxiv.files import LocalFileObj

from ...domain.publish import PublishPayload
from ...services.db import get_submission_with_html, write_published_html
from ...services.files import get_file_manager
# from ..convert import insert_base_tag, replace_absolute_anchors_for_doc
from ...services.latexml.metadata import generate_metadata_publish
from ...services.latexml import insert_base_tag, replace_relative_anchors
from .fastly_purge import fastly_purge_abs

logger = logging.getLogger()

def publish (payload: PublishPayload) -> None:
    try:
        # Check if there is an existing conversion for given submission.
        submission_row = get_submission_with_html (payload.submission_id)
        if submission_row is None:
            logger.info(f'No html found for {payload}')
            return
        else:
            logger.info(f'Identified successful conversion for {payload}')
        
        # Download submission conversion and rename. Return path to main .html file
        get_file_manager().download_submission_conversion(payload)
        logger.info(f'Successfully downloaded conversion {payload}')

        main_html_file_path = f'{get_file_manager().local_publish_store.prefix}{payload.paper_id.idv}/{payload.paper_id.idv}.html'

        insert_base_tag(payload.paper_id.idv, main_html_file_path)        
        replace_relative_anchors(f'{current_app.config["VIEW_DOC_BASE"]}/html/{payload.paper_id.idv}', main_html_file_path)
        logger.info(f'Successfully updated HTML for {payload}')
        
        submission_metadata = get_file_manager().local_publish_store.to_obj(f'{payload.paper_id.idv}/__metadata.json')
    
        assert isinstance(submission_metadata, LocalFileObj)
        with submission_metadata.open('r') as f:
            published_metadata = generate_metadata_publish(payload, f.read()) # type: ignore
        with submission_metadata.open('w') as f:
            f.write(published_metadata) # type: ignore
        logger.info(f'Successfully updated metadata for {payload}')

        write_published_html (payload.paper_id, submission_row)
        logger.info(f'Successfully wrote {payload} to announced DB')

        get_file_manager().upload_document_conversion(payload)
        logger.info(f'Successfully uploaded {payload} HTML to bucket')

        get_file_manager().clean_up_publish(payload)
        logger.info(f'Successfully cleaned up filesystem for {payload} announce')

        # Purge abs page from fastly so we can see it
        if not current_app.config['IS_DEV']:
            fastly_purge_abs(payload.paper_id, current_app.config['FASTLY_PURGE_KEY'])
    except Exception as e:
        try:
            logger.warning(f'Error publishing {payload}', exc_info=True)
        except:
            logger.warning(f'Error publishing unknown', exc_info=True)


    