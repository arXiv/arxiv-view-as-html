"""Module that handles the conversion process from LaTeX to HTML."""

import logging
from enum import Enum, auto

from flask import current_app

from ...domain.conversion import ConversionPayload, DocumentConversionPayload
from ...locking import id_lock
from ...services.db import write_failure, write_start, write_success
from ...services.files import get_file_manager
from ...services.latexml import html_asset_prefix, latexml, normalize_html_links
from ...services.latexml.metadata import generate_metadata_convert

logger = logging.getLogger()


class ConversionOutcome(Enum):
    """Outcome of a conversion attempt; the route maps it to the Pub/Sub ack/nack.

    Only TRANSIENT_FAILURE is retryable: the converter was killed by a signal (e.g.
    a cold-start-contention SIGSEGV, #248), which a redelivery typically clears.
    SUCCESS and PERMANENT_FAILURE are both acked -- a retry cannot change them.
    """

    SUCCESS = auto()
    PERMANENT_FAILURE = auto()
    TRANSIENT_FAILURE = auto()


def process(payload: ConversionPayload) -> ConversionOutcome:
    checksum: str | None = None
    # Flipped just before the upload so the except handler can tell a crash that
    # already overwrote the published HTML (downgrade the DB row to match) from one
    # before it (prior good HTML still live -> keep the row).
    bucket_touched = False
    try:
        fm = get_file_manager()
        lock_str = str(payload.identifier) if isinstance(payload.identifier, int) else payload.identifier.idv
        with id_lock(lock_str, current_app.config["LOCK_DIR"]):
            logger.info(f"starting conversion for {payload.identifier}")
            checksum, workdir = fm.download_source(payload)
            write_start(payload, checksum)
            fm.remove_ltxml(payload)

            latexml_output = latexml(payload, workdir)
            if latexml_output.returncode < 0:
                # A negative rc is a signal death (e.g. SIGSEGV -11), not an orderly
                # exit -- transient (#248). Return before uploading (no usable output)
                # without recording a failure, leaving the in-progress row for a
                # redelivery to finish; the route decides whether to nack.
                logger.error(f"LaTeXML killed by signal {-latexml_output.returncode} for {payload.identifier}")
                return ConversionOutcome.TRANSIENT_FAILURE
            logger.info(f"Successfully executed latexml on {payload}")

            output_dir = fm.latexml_output_dir_name(payload)
            metadata = generate_metadata_convert(payload, latexml_output.missing_packages)
            logger.info(f"Successfully generated metadata for {payload}")
            with open(f"{output_dir}__metadata.json", "w") as f:
                f.write(metadata)

            if isinstance(payload, DocumentConversionPayload):
                normalize_html_links(html_asset_prefix(payload.identifier), f"{output_dir}{payload.name}.html")
                logger.info(f"Successfully updated HTML for {payload}")

            if latexml_output.returncode == 0:
                write_success(payload, checksum)
                logger.info(f"Successfully wrote {payload} to announced DB")
                outcome = ConversionOutcome.SUCCESS
            else:
                # Orderly nonzero exit (fatal LaTeX error, timeout wrapper, or the
                # --max-memory watchdog exit 137): deterministic for this input, so ack.
                # The upload below overwrites the published HTML, so record the failure.
                write_failure(payload, checksum, bucket_clobbered=True)
                outcome = ConversionOutcome.PERMANENT_FAILURE

            # Note: There is a gap between when the user would see that html is ready and when it is uploaded.
            # In my opinion, this is a smaller problem than the user seeing an incorrect version of their html
            bucket_touched = True
            fm.upload_latexml(payload)
            logger.info(f"Successfully uploaded {payload} HTML to bucket")
            return outcome
    except Exception:
        logger.info(f"conversion unsuccessful for {payload.identifier}", exc_info=True)
        try:
            # Ack: an unexpected exception (missing source, malformed input, a code
            # error) will not clear on redelivery. Downgrade a prior success only if
            # the upload had already begun.
            write_failure(payload, checksum, bucket_clobbered=bucket_touched)
        except Exception as e:
            logger.error(f"failed to write failure for {payload.identifier}: {e}", exc_info=True)
        return ConversionOutcome.PERMANENT_FAILURE
