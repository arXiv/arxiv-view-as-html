from datetime import timezone
from email.utils import format_datetime
from pathlib import Path
import json
import logging
from flask import Response, make_response, stream_with_context

from arxiv.files import LocalFileObj
from .scaffold import ArticleScaffoldMetadata, HTMLFileTransform, render_branded_html_paper


def send_file_with_scaffold(path: Path, meta: ArticleScaffoldMetadata) -> Response:
    file = LocalFileObj(path)
    transformed = HTMLFileTransform(file, render_branded_html_paper, meta)
    # This logic matches the basics of arxiv-browse's
    # dissemination.default_resp_fn , followed by a scaffolding transform on the content.
    resp: Response = Response()
    # Flask/werkzeug automatically do Transfer-Encoding: chunked for a file
    resp = make_response(stream_with_context(iter(transformed.open("rb"))))
    # but the unit test client doesn't do that so we force it for those
    # see https://github.com/pallets/flask/issues/5424
    resp.headers["Transfer-Encoding"] = "chunked"
    # Don't set Content-Length, it will disable Transfer-Encoding: chunked

    resp.set_etag(file.etag)
    resp.headers["Last-Modified"] = format_datetime(file.updated.astimezone(timezone.utc), usegmt=True)
    resp.headers["Accept-Ranges"] = "bytes"
    resp.headers["Access-Control-Allow-Origin"] = "*"

    return resp

def submission_scaffold_metadata(submission_id : int, metadata_path : Path) -> ArticleScaffoldMetadata:
    # In the future, we may want to pull this from the database or GCS metadata, but for now we just hardcode it.
    try: 
        with open(metadata_path) as fh:
            data = json.load(fh)
        return ArticleScaffoldMetadata(
            license = data.get('license','No License'),
            page_id = str(submission_id),
            published = False,
            primary_category = data.get('primary_category',''),
            date_of_version = data.get('submission_timestamp',''))
    except Exception as e:
        logging.error(f"Failed to read {metadata_path} for submission scaffold, with {e}")
        return ArticleScaffoldMetadata(
            license = None,
            page_id = str(submission_id),
            published = False,
            primary_category = None,
            date_of_version = None
        )

BROWSE_VERSION = '0.3.4' # Move this to Dockerfile ?

def browse_urls_fallback(error, endpoint, values):
    if endpoint == "static":
        return f"/static/browse/{BROWSE_VERSION}/{values.get('filename')}"
    else:
        logging.error(f"URL build error for endpoint {endpoint} with values {values}")
        return None