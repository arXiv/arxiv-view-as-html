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
from .fastly_purge import fastly_purge_abs

logger = logging.getLogger()

def publish (payload: PublishPayload) -> None:
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         paylod (dict): Event payload containing a base64 encoded 
                        string of the json in the ['message']['data'] key    
    Steps:
      1. Parse out fields from json payload
      2. Query arXiv_latexml_sub to check for html for submission
         [continue to step 3 if exists else end]
      3. Copy HTML directory from latexml_submission_converted to 
         latexml_arxiv_id_converted with new name
      4. Write new row to arXiv_latexml_doc
      5. Delete from latexml_submission_converted

    """

    try:
        # Check if there is an existing conversion for given submission.
        submission_row = get_submission_with_html (payload.submission_id)
        if submission_row is None:
            logger.info(f'No html found for {payload}')
            return
        else:
            logger.info(f'Identified successful conversion for {payload}')
        
        # Download submission conversion and rename. Return path to main .html file
        # TODO: Move to file manager
        get_file_manager().download_submission_conversion(payload)
        logger.info(f'Successfully moved conversion {payload}')

        # Insert base tag
        # insert_base_tag(html_file, paper_idv)
        # logger.info(f'Successfully injected base tag for {submission_id}/{paper_idv}')

        # Inject watermark into html
        # insert_watermark(html_file, make_published_watermark(submission_id, paper_id, version))    
        # logger.info(f'Successfully injected watermark for {submission_id}/{paper_idv}')

        # replace_absolute_anchors_for_doc(html_file, paper_idv)
        # logger.info(f'Successfully replaced anchor tags for {submission_id}/{paper_idv}')

        submission_metadata = get_file_manager().local_publish_store.to_obj(f'{payload.paper_id.idv}/__metadata.json')
    
        assert isinstance(submission_metadata, LocalFileObj)
        with submission_metadata.open('r') as f:
            published_metadata = generate_metadata_publish(payload, f.read()) # type: ignore
        with submission_metadata.open('w') as f:
            f.write(published_metadata) # type: ignore

        write_published_html (payload.paper_id, submission_row)

        get_file_manager().upload_document_conversion(payload)

        get_file_manager().clean_up_publish(payload)

        # Move log output from sub bucket to published bucket
        # TODO: Move to file manager
        # move_sub_qa_to_doc_qa (submission_id, paper_idv)
        # logger.info(f'Successfully wrote {submission_id}/{paper_idv} qa to doc bucket')

        # # Purge abs page from fastly so we can see it
        # if not current_app.config['IS_DEV']:
        #     fastly_purge_abs(paper_id, version, current_app.config['FASTLY_PURGE_KEY'])

    # TODO: Clean this shit up
    except Exception as e:
        try:
            logger.warning(f'Error publishing {payload}', exc_info=True)
        except:
            logger.warning(f'Error publishing unknown', exc_info=True)