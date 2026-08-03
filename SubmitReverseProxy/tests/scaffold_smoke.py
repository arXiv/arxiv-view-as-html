"""Check that a branded HTML paper can actually be rendered, at image build time.

The scaffold templates and the state machine that drives them are vendored from arxiv-browse
and arxiv-base when the image is built, so a change upstream can break rendering here without
a single line of this repository changing. The response is streamed, so the failure surfaces
as a silently truncated paper rather than a 500 -- which is how it went unnoticed once already.

Run as a `RUN` step in dockerfiles/Dockerfile.*, this turns that class of breakage into a
failed build. It deliberately uses the same wiring as entry_point.py, via
`register_scaffold_urls`, so a misordered or missing URL handler fails here too.
"""
import logging
import sys
from pathlib import Path

import ReverseProxy.files
# The same shim entry_point.py installs, see the comment there.
sys.modules["arxiv.files"] = ReverseProxy.files

from flask import Flask, render_template
from ReverseProxy.scaffold import ArticleScaffoldMetadata
from ReverseProxy.scaffold_response import register_scaffold_urls, safe_render_branded_html_paper

FIXTURE = Path(__file__).parent / 'fixtures' / 'latexml_paper.html'
TEMPLATES = ['head_mixins.html', 'header.html', 'callout_license.html', 'footer.html']

# A failed URL build is logged rather than raised once a fallback handles it, so a page can
# render "fine" while filling the logs. Treat any error log during rendering as a failure.
class ErrorsAreFailures(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)
        self.records: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record.getMessage())


def main() -> int:
    errors = ErrorsAreFailures()
    logging.getLogger().addHandler(errors)

    app = Flask('ReverseProxy', static_folder=None)
    app.config.from_pyfile('config.py')
    app.config['SERVER_NAME'] = None
    register_scaffold_urls(app)

    # What routes.py builds for a submission preview, which is the only case this service has.
    meta = ArticleScaffoldMetadata(license='CC BY 4.0', page_id='7750266', published=False,
                                   primary_category='astro-ph.GA', date_of_version='2026-01-16')

    failures = []
    with app.test_request_context('/html/submission/7750266/view'):
        # Every scaffold template must render on its own ...
        rendered = {}
        for template in TEMPLATES:
            try:
                rendered[template] = render_template(
                    f'dissemination/article_scaffold/{template}', meta=meta)
            except Exception as e:
                failures.append(f"{template} does not render: {type(e).__name__}: {e}")

        # ... and the state machine must reach the end of the document, having inserted each
        # of them. Stalling midway is not an error, it just quietly drops the arXiv branding.
        state, out = 'head', []
        for line in FIXTURE.read_bytes().splitlines(keepends=True):
            state, transformed = safe_render_branded_html_paper(line, state, meta)
            out.append(transformed)
        body = b''.join(out).decode('utf-8')

        if state == 'noop':
            failures.append("transform aborted into 'noop' -- either scaffolding raised and the "
                            "guard caught it, or the fixture tripped the legacy JS passthrough")
        elif state != 'body_end':
            failures.append(f"transform ended in state {state!r}, expected 'body_end' -- the "
                            f"markup the state machine looks for has moved in {FIXTURE.name}")
        for template, content in rendered.items():
            if content.strip() and content not in body:
                failures.append(f"{template} is missing from the branded paper")
        if 'Generated on a smoke test by LaTeXML' in body:
            failures.append("the LaTeXML footer was not replaced by the arXiv one")

    failures.extend(f"error logged while rendering: {message}" for message in errors.records)

    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1
    print(f"scaffold smoke test OK ({len(TEMPLATES)} templates, {len(body)} bytes branded)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
