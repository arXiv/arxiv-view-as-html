"""Module that handles the conversion process from LaTeX to HTML."""

import logging
import traceback

from flask import current_app

from ...domain.conversion import ConversionPayload, DocumentConversionPayload
from ...locking import id_lock
from ...services.db import write_failure, write_start, write_success
from ...services.files import get_file_manager
from ...services.latexml import insert_base_tag, latexml, replace_relative_anchors
from ...services.latexml.metadata import generate_metadata_convert

logger = logging.getLogger()


def process(payload: ConversionPayload) -> None:
    try:
        if isinstance(payload.identifier, int):
            lock_str = str(payload.identifier)
        else:
            lock_str = payload.identifier.idv
        with id_lock(lock_str, current_app.config["LOCK_DIR"]):
            logger.info(f"starting conversion for {payload.identifier}")
            checksum, workdir = get_file_manager().download_source(payload)

            write_start(payload, checksum)

            get_file_manager().remove_ltxml(payload)

            latexml_output = latexml(payload, workdir)  # Also need to upload stdout
            logger.info(f"Successfully executed latexml on {payload}")

            metadata = generate_metadata_convert(payload, latexml_output.missing_packages)
            logger.info(f"Successfully generated metadata for {payload}")

            with open(f"{get_file_manager().latexml_output_dir_name(payload)}__metadata.json", "w") as f:
                f.write(metadata)
            # This is now written by the main latexml process, see the --log parameter.
            # with open(f"{get_file_manager().latexml_output_dir_name(payload)}__stdout.txt", "w") as f:
            #     f.write(latexml_output.output)

            if isinstance(payload, DocumentConversionPayload):
                main_html_file_path = f"{get_file_manager().latexml_output_dir_name(payload)}{payload.name}.html"
                insert_base_tag(payload.identifier.idv, main_html_file_path)
                replace_relative_anchors(
                    f'{current_app.config["VIEW_DOC_BASE"]}/html/{payload.identifier.idv}', main_html_file_path
                )
                logger.info(f"Successfully updated HTML for {payload}")
            if latexml_output.returncode == 0:
                write_success(payload, checksum)
                logger.info(f"Successfully wrote {payload} to announced DB")
            else:
                write_failure(payload, checksum)

            # Note: There is a gap between when the user would see that html is ready and when it is uploaded.
            # In my opinion, this is a smaller problem than the user seeing an incorrect version of their html
            get_file_manager().upload_latexml(payload)
            logger.info(f"Successfully uploaded {payload} HTML to bucket")
    except Exception:
        print(traceback.format_exc())
        logger.info(f"conversion unsuccessful for {payload.identifier}", exc_info=True)
        try:
            write_failure(payload, checksum)
        except Exception as e:
            logger.warning(f"failed to write failure for {payload.identifier}: {e}", exc_info=True)
