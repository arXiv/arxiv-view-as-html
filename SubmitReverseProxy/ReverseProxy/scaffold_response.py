from datetime import timezone
from email.utils import format_datetime
from pathlib import Path

from arxiv.document.metadata import DocMetadata
from arxiv.files import FileObj
from flask import Response, make_response, stream_with_context

from .scaffold import HTMLFileTransform, render_branded_html_paper


def send_file_with_scaffold(path: Path, docmeta: DocMetadata) -> Response:
    file = FileObj(path)
    transformed = HTMLFileTransform(file, render_branded_html_paper, docmeta)
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
    resp.headers["Last-Modified"] = format_datetime(fileobj.updated.astimezone(timezone.utc), usegmt=True)
    resp.headers["Accept-Ranges"] = "bytes"
    resp.headers["Access-Control-Allow-Origin"] = "*"

    return resp
