from datetime import timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import json
import logging
import os
from flask import Response, make_response, stream_with_context

from arxiv.files import LocalFileObj
from .scaffold import ArticleScaffoldMetadata, HTMLFileTransform, render_branded_html_paper


def safe_render_branded_html_paper(byte_line: bytes, state: str, meta: ArticleScaffoldMetadata) \
        -> Tuple[str, bytes]:
    """Never let a scaffolding failure truncate the paper.

    The scaffold templates are vendored from arxiv-browse at build time, so they can grow
    dependencies this service does not provide (an arxiv-base blueprint, a new endpoint...).
    Since the response is streamed, an exception raised mid-transform silently truncates the
    page to whatever bytes were already flushed -- typically a blank body under a valid head.
    Degrade to the unbranded LaTeXML HTML instead, and leave a loud trace in the logs.
    """
    try:
        return render_branded_html_paper(byte_line, state, meta)
    except Exception as e:
        logging.exception(
            f"HTML paper scaffolding failed in state {state!r}, serving unbranded HTML: {e}")
        # 'noop' is terminal, so the remainder of the document passes through unmodified.
        return ('noop', byte_line)


def send_file_with_scaffold(path: Path, meta: ArticleScaffoldMetadata) -> Response:
    file = LocalFileObj(path)
    transformed = HTMLFileTransform(file, safe_render_branded_html_paper, meta)
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

def _vendored_version(name: str, fallback: str) -> str:
    """The release the vendored `name` templates were copied from.

    Both projects serve their assets from a versioned path, so the Dockerfile bakes the
    version out of the very same checkout it copies the templates from -- markup and assets
    then cannot drift apart. It has to come from the checkout rather than from
    `importlib.metadata`, because the `arxiv-base` actually installed here is the older one
    `arxiv-auth` pins, not the one the templates came from.
    """
    try:
        version = Path(__file__).with_name(f'{name}_version.txt').read_text().strip()
    except Exception as e:
        logging.error(f"Failed to read the vendored {name} version, with {e}")
        version = ''
    return version or fallback

# arxiv-browse serves its own assets from /static/browse/<APP_VERSION>, see browse/config.py.
BROWSE_VERSION = os.environ.get('BROWSE_VERSION') or _vendored_version('browse', '0.3.4')
# arxiv-base serves the shared chrome from /static/base/<BASE_VERSION>, see arxiv/base/config.py,
# where it defaults to the installed distribution version, i.e. the one in its pyproject.toml.
ARXIV_BASE_VERSION = os.environ.get('ARXIV_BASE_VERSION') or _vendored_version('arxiv_base', '1.0.1')

def browse_urls_fallback(error: Exception, endpoint: str, values: Dict[str, Any]) -> Optional[str]:
    if endpoint == "static":
        # `services.arxiv.org` does route /static/browse/, so keep this one relative.
        return f"/static/browse/{BROWSE_VERSION}/{values.get('filename')}"
    elif endpoint == "base.static":
        # It does not route /static/base/ though, and this service never registers the
        # arxiv-base blueprint that would serve it -- so link the shared chrome assets off
        # the static host, the same one the conversion pipeline already uses.
        return f"https://static.arxiv.org/static/base/{ARXIV_BASE_VERSION}/{values.get('filename')}"
    else:
        logging.error(f"URL build error for endpoint {endpoint} with values {values}")
        return None
