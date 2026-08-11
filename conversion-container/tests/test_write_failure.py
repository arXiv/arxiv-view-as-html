"""Unit tests for `write_failure` and its `_write_failure_doc` / `_write_failure_sub` helpers.

These tests mock `transaction()` and the SQLAlchemy query chain so they do not
require a real database. They verify the four branches of the new logic:

  1. No prior row exists -> a new row is inserted with status=2.
  2. Prior row with status=1 and bucket_clobbered=False -> row preserved.
  3. Prior row with status=1 and bucket_clobbered=True -> row downgraded to status=2.
  4. Prior row with status=0 (mid-attempt) -> row updated to status=2 regardless of bucket_clobbered.
"""
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from flask import Flask

from arxiv.db.models import DBLaTeXMLDocuments, DBLaTeXMLSubmissions
from arxiv.identifier import Identifier

from conversion.domain.conversion import DocumentConversionPayload, SubmissionConversionPayload
from conversion.services import db as db_service


DOC_IDENTIFIER = Identifier("2401.12345v1")
SUB_IDENTIFIER = 987654
LATEST_CHECKSUM = "deadbeefcafebabe"
PRIOR_CHECKSUM = "aaaaaaaaaaaaaaaa"


@pytest.fixture
def mock_transaction(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, SimpleNamespace]:
    """Patch `transaction()` in the db module; yields a (session_mock, found_row_holder) pair.

    Tests set `holder.row` to the object that should be returned from the `.first()`
    call on the query chain (or None to simulate a missing row).
    """
    holder = SimpleNamespace(row=None)
    session = MagicMock(name="session")

    query = MagicMock(name="query")
    session.query.return_value = query
    query.filter.return_value = query

    def first_side_effect() -> object:
        return holder.row

    query.first.side_effect = first_side_effect

    @contextmanager
    def fake_transaction() -> Iterator[MagicMock]:
        yield session

    monkeypatch.setattr(db_service, "transaction", fake_transaction)
    return session, holder


def _make_existing_doc_row(conversion_status: int) -> MagicMock:
    row = MagicMock(spec=DBLaTeXMLDocuments)
    row.conversion_status = conversion_status
    row.tex_checksum = PRIOR_CHECKSUM
    row.latexml_version = "previous_commit_version"
    return row


def _make_existing_sub_row(conversion_status: int) -> MagicMock:
    row = MagicMock(spec=DBLaTeXMLSubmissions)
    row.conversion_status = conversion_status
    row.tex_checksum = PRIOR_CHECKSUM
    row.latexml_version = "previous_commit_version"
    return row


# ---------------------------------------------------------------------------
# DocumentConversionPayload branches
# ---------------------------------------------------------------------------

def test_write_failure_doc_inserts_when_no_prior_row(
    app: Flask, mock_transaction: tuple[MagicMock, SimpleNamespace]
) -> None:
    """Download-phase failure path: checksum may be None, no row exists yet."""
    session, holder = mock_transaction
    holder.row = None
    payload = DocumentConversionPayload(identifier=DOC_IDENTIFIER, single_file=False, is_latest=True)

    db_service.write_failure(payload, checksum=None)

    session.add.assert_called_once()
    inserted = session.add.call_args.args[0]
    assert isinstance(inserted, DBLaTeXMLDocuments)
    assert inserted.paper_id == DOC_IDENTIFIER.id
    assert inserted.document_version == DOC_IDENTIFIER.version
    assert inserted.conversion_status == 2
    assert inserted.latexml_version == "test_commit_version"
    assert inserted.tex_checksum is None
    assert inserted.conversion_start_time is not None
    assert inserted.conversion_end_time is not None


def test_write_failure_doc_preserves_prior_success_when_bucket_intact(
    app: Flask, mock_transaction: tuple[MagicMock, SimpleNamespace]
) -> None:
    """Exception before upload_latexml: bucket still holds good HTML -> do not downgrade."""
    session, holder = mock_transaction
    holder.row = _make_existing_doc_row(conversion_status=1)
    payload = DocumentConversionPayload(identifier=DOC_IDENTIFIER, single_file=False, is_latest=True)

    db_service.write_failure(payload, checksum=LATEST_CHECKSUM, bucket_clobbered=False)

    assert holder.row.conversion_status == 1  # untouched
    assert holder.row.tex_checksum == PRIOR_CHECKSUM  # untouched
    session.add.assert_not_called()


def test_write_failure_doc_overwrites_prior_success_when_bucket_clobbered(
    app: Flask, mock_transaction: tuple[MagicMock, SimpleNamespace]
) -> None:
    """returncode != 0 with upload: bucket is overwritten -> DB must reflect failure."""
    session, holder = mock_transaction
    holder.row = _make_existing_doc_row(conversion_status=1)
    payload = DocumentConversionPayload(identifier=DOC_IDENTIFIER, single_file=False, is_latest=True)

    db_service.write_failure(payload, checksum=LATEST_CHECKSUM, bucket_clobbered=True)

    assert holder.row.conversion_status == 2
    assert holder.row.tex_checksum == LATEST_CHECKSUM
    assert holder.row.latexml_version == "test_commit_version"
    assert holder.row.conversion_end_time is not None
    session.add.assert_not_called()


def test_write_failure_doc_updates_in_progress_row(
    app: Flask, mock_transaction: tuple[MagicMock, SimpleNamespace]
) -> None:
    """Normal mid-attempt failure: write_start left status=0, write_failure flips it to 2."""
    session, holder = mock_transaction
    holder.row = _make_existing_doc_row(conversion_status=0)
    payload = DocumentConversionPayload(identifier=DOC_IDENTIFIER, single_file=False, is_latest=True)

    db_service.write_failure(payload, checksum=LATEST_CHECKSUM, bucket_clobbered=False)

    assert holder.row.conversion_status == 2
    assert holder.row.tex_checksum == LATEST_CHECKSUM
    session.add.assert_not_called()


def test_write_failure_doc_resets_checksum_when_none(
    app: Flask, mock_transaction: tuple[MagicMock, SimpleNamespace]
) -> None:
    """When checksum is None (download-phase failure), the current attempt's state
    should be reflected by nulling the checksum so queries don't see stale data."""
    session, holder = mock_transaction
    holder.row = _make_existing_doc_row(conversion_status=0)
    payload = DocumentConversionPayload(identifier=DOC_IDENTIFIER, single_file=False, is_latest=True)

    db_service.write_failure(payload, checksum=None, bucket_clobbered=False)

    assert holder.row.conversion_status == 2
    assert holder.row.tex_checksum is None


# ---------------------------------------------------------------------------
# SubmissionConversionPayload branches (smoke coverage - logic mirrors doc)
# ---------------------------------------------------------------------------

def test_write_failure_sub_inserts_when_no_prior_row(
    app: Flask, mock_transaction: tuple[MagicMock, SimpleNamespace]
) -> None:
    session, holder = mock_transaction
    holder.row = None
    payload = SubmissionConversionPayload(identifier=SUB_IDENTIFIER, single_file=None)

    db_service.write_failure(payload, checksum=None)

    session.add.assert_called_once()
    inserted = session.add.call_args.args[0]
    assert isinstance(inserted, DBLaTeXMLSubmissions)
    assert inserted.submission_id == SUB_IDENTIFIER
    assert inserted.conversion_status == 2


def test_write_failure_sub_overwrites_prior_success_when_bucket_clobbered(
    app: Flask, mock_transaction: tuple[MagicMock, SimpleNamespace]
) -> None:
    session, holder = mock_transaction
    holder.row = _make_existing_sub_row(conversion_status=1)
    payload = SubmissionConversionPayload(identifier=SUB_IDENTIFIER, single_file=None)

    db_service.write_failure(payload, checksum=LATEST_CHECKSUM, bucket_clobbered=True)

    assert holder.row.conversion_status == 2


def test_write_failure_sub_preserves_prior_success_when_bucket_intact(
    app: Flask, mock_transaction: tuple[MagicMock, SimpleNamespace]
) -> None:
    session, holder = mock_transaction
    holder.row = _make_existing_sub_row(conversion_status=1)
    payload = SubmissionConversionPayload(identifier=SUB_IDENTIFIER, single_file=None)

    db_service.write_failure(payload, checksum=LATEST_CHECKSUM, bucket_clobbered=False)

    assert holder.row.conversion_status == 1
