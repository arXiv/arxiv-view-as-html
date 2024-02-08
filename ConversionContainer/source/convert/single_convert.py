import uuid
import os
import shutil
import logging
import traceback

from flask import current_app

from ..util.db_queries import (
    get_process_data_from_db,
    get_source_flags_for_submission
)

from . import process
from ..publish import _publish

def single_convert (paper_id: str, version: int):
    try:
        submission_id, source_flags = get_process_data_from_db(paper_id, version)
    except:
        raise
    
    single_file = '1' in source_flags

    blob = f'{submission_id}/{submission_id}.gz' if single_file else f'{submission_id}/{submission_id}.tar.gz'
    bucket = current_app.config['IN_BUCKET_SUB_ID']

    process(submission_id, blob, bucket, single_file)

    _publish(submission_id, paper_id, version)

def reconvert_submission (submission_id: int) -> bool:
    try:
        source_flags = get_source_flags_for_submission(submission_id)
    except:
        raise
    
    single_file = '1' in source_flags

    blob = f'{submission_id}/{submission_id}.gz' if single_file else f'{submission_id}/{submission_id}.tar.gz'
    bucket = current_app.config['IN_BUCKET_SUB_ID']

    process(submission_id, blob, bucket, single_file)