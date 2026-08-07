import os
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest
from flask import Flask

from conversion.domain.conversion import LaTeXMLOutput, SubmissionConversionPayload
from conversion.services.files import get_file_manager
from conversion.services.latexml import clean_up_stale_assets, latexml


def call_bare_latexml(app: Flask, config: dict[str, Any]) -> LaTeXMLOutput:
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


TIMEOUT_TEX_CONTENT = r"\def\oops{test \oops here}\oops\bye"


@pytest.mark.call_latexml_tests
@pytest.mark.xfail(
    strict=False,
    reason="latexml-oxide's internal guards can race behind the Python subprocess wrapper on slow CI runners; canary for the internal-guard path",
)
def test_latexml_internal_timeout_marker(app: Flask) -> None:
    # latexml-oxide catches this runaway internally (for this input, the
    # box-count recursion guard fires deterministically before the wall-clock
    # timer) and writes a `Fatal:` record to the --log file before exiting 1.
    # The wall-clock timer instead emits `Fatal:timeout:wallclock` to stderr.
    config = {"LATEXML_TIMEOUT_SEC": 1, "TEST_TEX_CONTENT": TIMEOUT_TEX_CONTENT}
    result = call_bare_latexml(app, config)
    assert result.log is not None and "Fatal:" in result.log
    assert result.returncode == 1


@pytest.mark.call_latexml_tests
def test_latexml_timeout_terminates(app: Flask, caplog: pytest.LogCaptureFixture) -> None:
    latexml_timeout = 1
    wrapper_timeout = latexml_timeout + 5  # from conversion/services/latexml/__init__.py
    config = {"LATEXML_TIMEOUT_SEC": latexml_timeout, "TEST_TEX_CONTENT": TIMEOUT_TEX_CONTENT}
    caplog.clear()
    result = call_bare_latexml(app, config)
    # Infinite recursion must terminate via *one* of the two code paths: the engine
    # catches it internally (a recursion/timeout/oom guard, logged as a `Fatal:`
    # record in the --log file, exit nonzero), or the Python subprocess wrapper
    # kills it after wrapper_timeout. A match on either rules out other failure modes.
    terminated_internally = result.log is not None and "Fatal:" in result.log
    timed_out_by_wrapper = any(
        r.getMessage() == f"LaTeXML conversion timed out after {wrapper_timeout} seconds"
        for r in caplog.records
    )
    assert terminated_internally or timed_out_by_wrapper
    assert result.returncode == 1


@pytest.mark.call_latexml_tests
def test_clean_up_stale_assets(app: Flask) -> None:
    with tempfile.TemporaryDirectory() as workdir:
        test_file_path = f"{workdir}/test.tex"
        with open(test_file_path, "w") as file:
            file.write("sample")
        test_dir_path = f"{workdir}/test_dir"
        os.mkdir(f"{workdir}/test_dir")
        time.sleep(1)
        assert os.path.exists(test_file_path)
        assert os.path.exists(test_dir_path)
        clean_up_stale_assets(Path(workdir), 0)
        assert not (os.path.exists(test_file_path))
        assert not (os.path.exists(test_dir_path))
