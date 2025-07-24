import logging
import os
import tempfile
import time
from pathlib import Path

import pytest

from conversion.domain.conversion import LaTeXMLOutput, SubmissionConversionPayload
from conversion.services.files import get_file_manager
from conversion.services.latexml import clean_up_stale_assets, latexml


def call_bare_latexml(app, config=dict | None) -> LaTeXMLOutput:
    """Call bare latexml without any additional configuration (no ar5iv paths or additions)."""
    with app.app_context():
        with tempfile.TemporaryDirectory() as workdir:
            app.config["LOCAL_CONVERSION_DIR"] = workdir
            app.config["LOCAL_PUBLISH_DIR"] = f"{workdir}/html"
            app.config["LATEXML_LOG_FILE"] = "__stdout.txt"
            # Empty, we do not have the dockerized ar5iv additions here
            app.config["LATEXML_PATHS"] = []
            app.config["LATEXML_PRELOADS"] = []
            for key, value in config.items():
                app.config[key] = value
            with open(f"{workdir}/test.tex", "w") as file:
                file.write(config["TEST_TEX_CONTENT"])
            payload = SubmissionConversionPayload(identifier=123, single_file=None)
            output_dirname = get_file_manager().latexml_output_dir_name(payload)
            result = latexml(payload, Path(workdir))

            latexml_log_path = Path(output_dirname + app.config["LATEXML_LOG_FILE"])
            assert latexml_log_path.exists()
            with open(latexml_log_path) as latexml_log_file:
                result.log = latexml_log_file.read()
            return result


@pytest.mark.call_latexml_tests
def test_latexml_timeout(app):
    config = {
        "LATEXML_TIMEOUT_SEC": 1,
        "TEST_TEX_CONTENT": r"\def\oops{test \oops here}\oops\bye",
    }
    result = call_bare_latexml(app, config)
    logging.warning(f"RESULT: {result}")
    assert "Fatal:timeout:timedout" in result.log
    assert result.returncode == 1


@pytest.mark.call_latexml_tests
def test_clean_up_stale_assets(app):
    with tempfile.TemporaryDirectory() as workdir:
        test_file_path = f"{workdir}/test.tex"
        with open(test_file_path, "w") as file:
            file.write("sample")
        test_dir_path = f"{workdir}/test_dir"
        os.mkdir(f"{workdir}/test_dir")
        time.sleep(1)
        assert os.path.exists(test_file_path)
        assert os.path.exists(test_dir_path)
        clean_up_stale_assets(workdir, 0)
        assert not (os.path.exists(test_file_path))
        assert not (os.path.exists(test_dir_path))
