from typing import Dict, Tuple
import logging

from ..models.util import transaction

from .db_queries import submission_has_html, \
    write_published_html
from .buckets import move_sub_to_doc_bucket, delete_sub

def _parse_json_payload (payload: Dict) -> Tuple[int, str, int]:
    return (
        payload['submission_id'],
        payload['paper_id'],
        payload['version']
    )

def publish (payload: Dict):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    
    Steps:
      1. Parse out fields from json payload
      2. Query arXiv_latexml_sub to check for html for submission
         [continue to step 3 if exists else end]
      3. Copy HTML directory from latexml_submission_converted to 
         latexml_arxiv_id_converted with new name
      4. Write new row to arXiv_latexml_doc
      5. Delete from latexml_submission_converted

    """

    # 1.
    submission_id, paper_id, version = _parse_json_payload(payload)
    paper_idv = f'{paper_id}v{version}'

    # If there is a db error, the session will be rolled back, but 
    # the document bucket may still get the site
    with transaction() as session:
        # 2.
        submission_row = submission_has_html(submission_id, session)
        if submission_row is None:
            logging.info(f'No html found for submission {submission_id}')
            return
        
        # 3.
        move_sub_to_doc_bucket (submission_id, paper_idv)

        # 4. 
        write_published_html (paper_id, version, submission_row, session)
    
        # 5. 
        delete_sub (submission_id)    


    