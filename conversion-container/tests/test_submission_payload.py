import pytest
from conversion.domain.conversion import SubmissionConversionPayload
from conversion.services.files import get_file_manager


@pytest.mark.filestore_unit_tests
def test_fetch_tar_gz(app):
    with app.app_context():
        manager = get_file_manager()
        obj = manager.source_payload_to_file_obj(SubmissionConversionPayload(identifier=1234, single_file=None))
        assert obj.exists()
        assert obj.name == "1234.tar"


@pytest.mark.filestore_unit_tests
def test_fetch_gz(app):
    with app.app_context():
        manager = get_file_manager()
        obj = manager.source_payload_to_file_obj(SubmissionConversionPayload(identifier=2345, single_file=None))
        assert obj.exists()
        assert obj.name == "2345"
