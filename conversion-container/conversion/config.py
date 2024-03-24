"""Config that specifies output bucket name for uploading converted articles"""

import os
from arxiv.config import Settings as BaseSettings

class Settings (BaseSettings):
    SUBMISSION_SOURCE_BUCKET: str
    DOCUMENT_SOURCE_BUCKET: str
    SUBMISSION_CONVERTED_BUCKET: str
    DOCUMENT_CONVERTED_BUCKET: str
    RAW_LATEXML_SUBMISSION: str

    QA_BUCKET_SUB: str
    QA_BUCKET_DOC: str

    LATEXML_COMMIT: str

    LATEXML_URL_BASE: str
    VIEW_SUB_BASE: str
    VIEW_DOC_BASE: str

    FASTLY_PURGE_KEY: str = 'no-key-dev'
    IS_DEV: bool = True

    LOCAL_CONVERSION_DIR = '/arxiv/extracted/'
    LOCAL_PUBLISH_DIR = '/arxiv/publish/'
    LOCK_DIR: str = '/arxiv/locks/'