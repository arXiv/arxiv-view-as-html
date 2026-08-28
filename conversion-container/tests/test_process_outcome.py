"""Outcome classification and push-route ack/nack disposition (#248).

Covers `conversion.processes.convert.process()` and the Pub/Sub disposition of the
push routes (arXiv/arxiv-view-as-html#248).

`process()` must:
  * return SUCCESS, upload, and write_success on an rc == 0 run;
  * return PERMANENT_FAILURE but STILL upload (publishing whatever oxide produced)
    and write_failure(bucket_clobbered=True) on an orderly nonzero exit (rc > 0);
  * return TRANSIENT_FAILURE on a signal death (rc < 0, e.g. SIGSEGV) WITHOUT
    uploading and WITHOUT recording a DB failure -- write_start already set the row
    to in-progress, so leaving it lets a redelivery (or the still-published prior
    HTML) win instead of downgrading a good row with an empty/partial run;
  * on an unexpected exception, record a failure whose bucket_clobbered reflects
    whether the upload had already begun, and return PERMANENT_FAILURE.

The routes must return 503 (nack -> redeliver) for a TRANSIENT_FAILURE only when
NACK_ON_TRANSIENT_FAILURE is enabled, and 200 (ack) in every other case.
"""
import logging
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from flask import Flask

from conversion import routes as routes_mod
from conversion.domain.conversion import LaTeXMLOutput, SubmissionConversionPayload
from conversion.processes import convert as convert_mod
from conversion.processes.convert import ConversionOutcome, process
from conversion.services.latexml import latexml

SUB_PAYLOAD = SubmissionConversionPayload(identifier=123, single_file=None)


# ---------------------------------------------------------------------------
# process() outcome classification
# ---------------------------------------------------------------------------

@pytest.fixture
def harness(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> SimpleNamespace:
    """Patch every collaborator of process() and hand back the mocks + an rc setter."""
    workdir = tmp_path / "src"
    workdir.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    fm = MagicMock(name="file_manager")
    fm.download_source.return_value = ("checksum123", workdir)
    fm.latexml_output_dir_name.return_value = f"{out_dir}/"
    monkeypatch.setattr(convert_mod, "get_file_manager", lambda: fm)

    @contextmanager
    def fake_lock(*_a: Any, **_k: Any) -> Iterator[None]:
        yield

    monkeypatch.setattr(convert_mod, "id_lock", fake_lock)

    write_start = MagicMock(name="write_start")
    write_success = MagicMock(name="write_success")
    write_failure = MagicMock(name="write_failure")
    monkeypatch.setattr(convert_mod, "write_start", write_start)
    monkeypatch.setattr(convert_mod, "write_success", write_success)
    monkeypatch.setattr(convert_mod, "write_failure", write_failure)

    monkeypatch.setattr(convert_mod, "generate_metadata_convert", MagicMock(return_value="{}"))
    monkeypatch.setattr(convert_mod, "normalize_html_links", MagicMock())

    def set_returncode(rc: int) -> None:
        monkeypatch.setattr(
            convert_mod,
            "latexml",
            lambda payload, wd: LaTeXMLOutput(returncode=rc, log=None, missing_packages=[]),
        )

    return SimpleNamespace(
        fm=fm,
        write_start=write_start,
        write_success=write_success,
        write_failure=write_failure,
        set_returncode=set_returncode,
    )


def test_success_uploads_and_writes_success(app: Flask, harness: SimpleNamespace) -> None:
    harness.set_returncode(0)
    outcome = process(SUB_PAYLOAD)
    assert outcome is ConversionOutcome.SUCCESS
    harness.write_success.assert_called_once()
    harness.write_failure.assert_not_called()
    harness.fm.upload_latexml.assert_called_once()


def test_nonzero_exit_is_permanent_and_still_uploads(app: Flask, harness: SimpleNamespace) -> None:
    harness.set_returncode(1)
    outcome = process(SUB_PAYLOAD)
    assert outcome is ConversionOutcome.PERMANENT_FAILURE
    harness.write_success.assert_not_called()
    harness.write_failure.assert_called_once()
    assert harness.write_failure.call_args.kwargs["bucket_clobbered"] is True
    # status quo: a broken-but-orderly run still publishes what it produced.
    harness.fm.upload_latexml.assert_called_once()


def test_mem_watchdog_exit_137_is_permanent(app: Flask, harness: SimpleNamespace) -> None:
    # oxide's --max-memory watchdog exits 137 (positive, not signal-killed): the
    # paper is over budget deterministically, so ack rather than retry forever.
    harness.set_returncode(137)
    outcome = process(SUB_PAYLOAD)
    assert outcome is ConversionOutcome.PERMANENT_FAILURE
    harness.fm.upload_latexml.assert_called_once()


def test_signal_kill_is_transient_no_upload_no_failure(app: Flask, harness: SimpleNamespace) -> None:
    harness.set_returncode(-11)  # SIGSEGV -- the #248 cold-start crash
    outcome = process(SUB_PAYLOAD)
    assert outcome is ConversionOutcome.TRANSIENT_FAILURE
    harness.write_success.assert_not_called()
    harness.write_failure.assert_not_called()  # do not downgrade the in-progress row
    harness.fm.upload_latexml.assert_not_called()  # do not overwrite good HTML with a crash


def test_exception_before_upload_preserves_bucket(
    app: Flask, harness: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness.set_returncode(0)
    monkeypatch.setattr(convert_mod, "generate_metadata_convert", MagicMock(side_effect=RuntimeError("boom")))
    outcome = process(SUB_PAYLOAD)
    assert outcome is ConversionOutcome.PERMANENT_FAILURE
    harness.fm.upload_latexml.assert_not_called()
    harness.write_failure.assert_called_once()
    assert harness.write_failure.call_args.kwargs["bucket_clobbered"] is False


def test_exception_during_upload_clobbers_bucket(app: Flask, harness: SimpleNamespace) -> None:
    harness.set_returncode(0)
    harness.fm.upload_latexml.side_effect = RuntimeError("upload boom")
    outcome = process(SUB_PAYLOAD)
    assert outcome is ConversionOutcome.PERMANENT_FAILURE
    harness.write_failure.assert_called_once()
    assert harness.write_failure.call_args.kwargs["bucket_clobbered"] is True


# ---------------------------------------------------------------------------
# Route ack/nack disposition
# ---------------------------------------------------------------------------

def _post(app: Flask, path: str, monkeypatch: pytest.MonkeyPatch, outcome: ConversionOutcome) -> Any:
    monkeypatch.setattr(routes_mod, "process", lambda payload: outcome)
    monkeypatch.setattr(routes_mod, "unwrap_document_conversion_payload", lambda body: SUB_PAYLOAD)
    monkeypatch.setattr(routes_mod, "unwrap_submission_conversion_payload", lambda body: SUB_PAYLOAD)
    return app.test_client().post(path, json={"message": {"data": ""}})


@pytest.mark.parametrize("path", ["/single-convert", "/process"])
def test_route_nacks_transient_when_enabled(app: Flask, monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    app.config["NACK_ON_TRANSIENT_FAILURE"] = True
    resp = _post(app, path, monkeypatch, ConversionOutcome.TRANSIENT_FAILURE)
    assert resp.status_code == 503


@pytest.mark.parametrize("path", ["/single-convert", "/process"])
def test_route_acks_transient_when_disabled(app: Flask, monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    app.config["NACK_ON_TRANSIENT_FAILURE"] = False
    resp = _post(app, path, monkeypatch, ConversionOutcome.TRANSIENT_FAILURE)
    assert resp.status_code == 200


@pytest.mark.parametrize("outcome", [ConversionOutcome.SUCCESS, ConversionOutcome.PERMANENT_FAILURE])
def test_route_acks_success_and_permanent_even_when_nack_enabled(
    app: Flask, monkeypatch: pytest.MonkeyPatch, outcome: ConversionOutcome
) -> None:
    app.config["NACK_ON_TRANSIENT_FAILURE"] = True
    resp = _post(app, "/single-convert", monkeypatch, outcome)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# oxide crash output is logged on a nonzero exit (issue #248, item 3)
# ---------------------------------------------------------------------------

def test_latexml_logs_oxide_output_on_nonzero_exit(
    app: Flask, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class _Result:
        returncode = -11
        stdout = "SIGSEGV: address boundary error\nBacktrace: oxide::main"

    monkeypatch.setattr("conversion.services.latexml.subprocess.run", lambda *a, **k: _Result())
    with tempfile.TemporaryDirectory() as workdir:
        app.config["LOCAL_CONVERSION_DIR"] = workdir
        app.config["LOCAL_PUBLISH_DIR"] = f"{workdir}/html"
        app.config["LATEXML_PATHS"] = []
        app.config["LATEXML_PRELOADS"] = []
        with caplog.at_level(logging.ERROR):
            output = latexml(SUB_PAYLOAD, Path(workdir))
    assert output.returncode == -11
    assert any("SIGSEGV: address boundary error" in r.getMessage() for r in caplog.records)
