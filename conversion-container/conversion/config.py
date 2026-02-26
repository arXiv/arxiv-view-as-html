"""Config that specifies output bucket name for uploading converted articles."""

from arxiv.config import Settings as BaseSettings


class Settings(BaseSettings):
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

    FASTLY_PURGE_KEY: str = "no-key-dev"
    IS_DEV: bool = True
    IS_FULL_CORPUS_CONVERT_MACHINE: bool = False

    LOCAL_CONVERSION_DIR: str = "/arxiv/extracted/"
    LOCAL_PUBLISH_DIR: str = "/arxiv/publish/"
    LOCK_DIR: str = "/arxiv/locks/"
