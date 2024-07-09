import pytest

from flask import Flask

from arxiv.files import LocalFileObj
from arxiv.files.object_store import LocalObjectStore
from arxiv.identifier import Identifier
from conversion.factory import create_web_app
from conversion.domain.conversion import (
    DocumentConversionPayload,
    SubmissionConversionPayload,
    LaTeXMLOutput
)
from conversion.services.latexml import list_missing_packages
from conversion.services.files import FileManager

LATEXML_DB_URI = 'sqlite:///:memory:?cache=latexml'
CLASSIC_DATABASE_URI = 'sqlite:///:memory:'

TESTING_CONFIG = {
    'SUBMISSION_SOURCE_BUCKET': 'tests/data/submission-data/',
    'DOCUMENT_SOURCE_BUCKET': 'tests/data/document-data/',
    'SUBMISSION_CONVERTED_BUCKET': 'tests/data/submission-conversions/',
    'DOCUMENT_CONVERTED_BUCKET': 'tests/data/document-conversions/',

    'CLASSIC_DATABASE_URI': 'sqlite:///:memory:',

    'QA_BUCKET_SUB': 'tests/data/qa-sub/',
    'QA_BUCKET_DOC': 'tests/data/qa-doc/',

    'LATEXML_COMMIT': 'test_commit_version',

    'LATEXML_DB_URI': LATEXML_DB_URI,
    'CLASSIC_DB_URI': CLASSIC_DATABASE_URI,

    'LOCK_DIR': 'tests/data/locks/'
}

def get_test_config():
    return TESTING_CONFIG.copy()

@pytest.fixture
def app():
    app = create_web_app(get_test_config())
    return app

@pytest.fixture
def mock_latexml(mocker):
    with open('tests/data/sample_latexml_stdout.txt') as f:
        output = f.read()
    missing_packages = list_missing_packages(output)

    assert len(missing_packages) == 2
    assert missing_packages[0] == 'fontawesome'
    assert missing_packages[1] == 'mhchem'

    mocker.patch('conversion.services.latexml.latexml', return_value=LaTeXMLOutput(output, missing_packages))

@pytest.fixture
def mock_file_manager(mocker):
    mock_file_manager = mocker.MagicMock(spec=FileManager)

    mock_file_manager.download_source.return_value = ('fake_checksum', LocalFileObj('fake_file'))
    mock_file_manager.upload_latexml.return_value = None
    mock_file_manager.remove_latexml.return_value = None
    mock_file_manager.clean_up_conversion.return_value = None
    mock_file_manager.clean_up_publish.return_value = None
    mock_file_manager.download_submission_conversion.return_value = None
    mock_file_manager.upload_document_conversion.return_value = None

    mocker.patch('conversion.services.files.get_file_manager', return_value=mock_file_manager)

@pytest.fixture
def doc_payload_latest():
    return DocumentConversionPayload(
        identifier=Identifier('2012.02198v2'),
        is_latest=True,
        single_file=False
    )

@pytest.fixture
def doc_payload_orig():
    return DocumentConversionPayload(
        identifier=Identifier('2012.02198v1'),
        is_latest=False,
        single_file=False
    )

@pytest.fixture
def doc_payload_single_file():
    return DocumentConversionPayload(
        identifier=Identifier('cs/0001013v2'),
        is_latest=False,
        single_file=True
    )

@pytest.fixture
def sub_payload():
    return SubmissionConversionPayload(
        identifier=Identifier(5246136),
        single_file=False
    )

@pytest.fixture
def sub_payload_single_file():
    return SubmissionConversionPayload(
        identifier=Identifier(5246125),
        single_file=True
    )