import json
import os
from time import sleep

from sqlalchemy import create_engine
from sqlalchemy.engine import Row
from sqlalchemy.exc import OperationalError

import functions_framework
from google.cloud.pubsub_v1 import PublisherClient

"""
Gather Environment Variables

This section should crash the program on fail
"""
PROJECT_ID = os.environ['PROJECT_ID']
TOPIC_ID = os.environ['TOPIC_ID']
DB_URI = os.environ['DB_URI']


@functions_framework.cloud_event
def main(cloud_event):

    """ GCP API's and DB connector """
    publisher = PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)
    engine = create_engine(DB_URI)

    """ 
    Fetch Rows

    This section should crash the program on fail. Cloud function retry will attempt it again
    """
    query = 'select submission_id, document_id, paper_id, version, type \
            from arXiv_next_mail \
            where mail_id = (select max(mail_id) \
                            from arXiv_next_mail)'
    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()

    """ Send Events """
    def _format_payload (row: Row) -> str: 
        return json.dumps({k: row[k] for k in row._mapping.keys()}).encode('utf-8')

    for i, row in enumerate(rows):
        if i % 50 == 0:
            sleep(3)
        try: # We don't want to crash on one failed _format_payload or pub fire
            future = publisher.publish(topic_path, _format_payload(row))
            res = future.result()
            print (f'{_format_payload(row)}: {res}')
        except Exception as e:
            print (f'WARNING: {str(e)}')
