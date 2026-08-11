from collections.abc import Generator
from os.path import abspath, dirname
from typing import Any

import pytest
from flask import Flask

from conversion.factory import create_web_app

package_path = abspath(dirname(dirname(__file__)))

LATEXML_DB_URI = "sqlite:///:memory:?cache=latexml"
CLASSIC_DATABASE_URI = "sqlite:///:memory:"

TESTING_CONFIG = {
    "QA_BUCKET_SUB": "",
    "QA_BUCKET_DOC": f"{package_path}/tests/data/",
    "LATEXML_OXIDE_VERSION": "test_commit_version",
    "LATEXML_DB_URI": LATEXML_DB_URI,
    "LOCK_DIR": "/arxiv/locks",
    "SUBMISSION_SOURCE_BUCKET": f"{package_path}/tests/data/",
    "DOCUMENT_SOURCE_BUCKET": f"{package_path}/tests/data/",
    "SUBMISSION_CONVERTED_BUCKET": f"{package_path}/tests/data/",
    "DOCUMENT_CONVERTED_BUCKET": f"{package_path}/tests/data/",
    "RAW_LATEXML_SUBMISSION": "",
    "LATEXML_URL_BASE": "/static/browse/0.3.4",
    "VIEW_SUB_BASE": "",
    "VIEW_DOC_BASE": "",
}


def test_config() -> dict[str, Any]:
    return TESTING_CONFIG.copy()


@pytest.fixture(scope="function")
def app() -> Generator[Flask, None, None]:
    conf = test_config()
    app = create_web_app(**conf)
    with app.app_context():
        yield app
