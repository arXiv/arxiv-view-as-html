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
    # latexml-oxide resource ceilings, env-overridable. Declared here (not just
    # read via config.get) so `app.config.from_object(Settings())` populates them
    # -- otherwise the env vars never reach app.config. Size LATEXML_MEM_LIMIT_BYTES
    # below the host RAM so oxide's --max-memory watchdog aborts gracefully first.
    LATEXML_MEM_LIMIT_BYTES: int = 6 * 1024**3
    LATEXML_TIMEOUT_SEC: int = 180

    VIEW_SUB_BASE: str
    VIEW_DOC_BASE: str

    FASTLY_PURGE_KEY: str = "no-key-dev"
    IS_DEV: bool = True
    IS_FULL_CORPUS_CONVERT_MACHINE: bool = False

    LOCAL_CONVERSION_DIR: str = "/arxiv/extracted/"
    LOCAL_PUBLISH_DIR: str = "/arxiv/publish/"
    LOCK_DIR: str = "/arxiv/locks/"
