from typing import Dict, Tuple
import logging
from base64 import b64decode
import json
from flask import current_app

from ..models.util import transaction, db

from .db_queries import submission_has_html, \
    write_published_html
from .buckets import (
    download_sub_to_doc_dir,
    upload_dir_to_doc_bucket, 
    delete_sub,
    move_sub_qa_to_doc_qa
)
from .watermark import make_published_watermark, insert_watermark

def _parse_json_payload (payload: Dict) -> Tuple[int, str, int]:
    data = json.loads(b64decode(payload['message']['data']).decode('utf-8'))
    return (
        data['submission_id'],
        data['paper_id'],
        data['version']
    )

def publish (payload: Dict):
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
    logging.info(payload['message'])

    # 1.
    submission_id, paper_id, version = _parse_json_payload(payload)
    paper_idv = f'{paper_id}v{version}'

    # If there is a db error, the session will be rolled back, but 
    # the document bucket may still get the site
    
    # with transaction() as session:
    with current_app.app_context():
    # Check if there is an existing conversion for given submission.
        submission_row = submission_has_html(submission_id, db.session)
        if submission_row is None:
            logging.info(f'No html found for submission {submission_id}')
            return
    
    # Download submission conversion and rename. Return path to main .html file
    html_file = download_sub_to_doc_dir(submission_id, paper_idv)

    with current_app.app_context():
        # Inject watermark into html
        insert_watermark(html_file, 
                            make_published_watermark(submission_id, paper_id, version))                 
    
    # Upload directory to published conversion bucket
    upload_dir_to_doc_bucket (paper_idv)

    # Update database accordingly
    write_published_html (paper_id, version, submission_row, db.session)

    db.session.commit()
    db.session.close()

    # Move log output from sub bucket to published bucket
    move_sub_qa_to_doc_qa (submission_id, paper_idv)

    # Delete from gcs
    # delete_sub (submission_id)


    