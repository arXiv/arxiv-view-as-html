"""Tests for HTML link normalisation (conversion.services.latexml.rewrite_link).

Guards against the broken-link class in arXiv/html_feedback#6854: scheme-less
external references (bare DOIs, emails, `www.`/host URLs) must be absolutised so
they never resolve under /html/<id>/ and 404. Only host-less references to a
servable in-paper asset get the paper-id prefix.
"""
import tempfile
from pathlib import Path

import pytest

from conversion.services.latexml import normalize_html_links, rewrite_link

ID = "2608.05281v1"

# --- untouched: already absolute / non-navigable ---------------------------
UNTOUCHED = [
    "https://example.com/path",
    "http://x.org",
    "mailto:someone@example.org",
    "ftp://ftp.example.com/f",
    "tel:+1234567890",
    "data:image/png;base64,AAA",
    "/abs/1234",
    "/static/browse/0.3.4/css/arxiv-html-papers-20260807.css",
    "#S1",
    "//cdn.example.com/x",
    "?q=1",
    "",
]

# --- scheme-less references that must go absolute OFF arXiv, never prefixed --
#   emails / DOIs / hosts (issue #6854 class A), host-less non-servable paths,
#   and -- the key counter-examples -- third-party links that happen to end in a
#   servable extension (must NOT be tangled into /html/<id>/).
ABSOLUTISED = [
    ("10.1038/30918", "https://doi.org/10.1038/30918"),
    ("ryan.cotterell@inf.ethz.ch", "mailto:ryan.cotterell@inf.ethz.ch"),
    ("timleung@uw.edu", "mailto:timleung@uw.edu"),
    ("www.tng-project.org/data", "https://www.tng-project.org/data"),
    ("www.sdss5.org", "https://www.sdss5.org"),
    ("dx.doi.org/10.1016/j.cognition.2010.10.004", "https://dx.doi.org/10.1016/j.cognition.2010.10.004"),
    ("scaling-diffusion-policy.github.io", "https://scaling-diffusion-policy.github.io"),
    ("www.mosaicml.com/blog/mpt-7b", "https://www.mosaicml.com/blog/mpt-7b"),
    # third-party links ending in a servable extension -> host wins, stay off arXiv
    ("example.com/logo.png", "https://example.com/logo.png"),
    ("www.foo.com/page.html", "https://www.foo.com/page.html"),
    # host-less references to a non-servable extension -> would only 404 locally
    ("figs/er1_shaw.eps", "https://figs/er1_shaw.eps"),
    ("results.pdf", "https://results.pdf"),
    ("section2", "https://section2"),
]

# --- genuine host-less in-paper resources -> prefixed ----------------------
PREFIXED = [
    "x1.png",
    "Plots/model2_final.jpg",
    "figures/images/a/reverse_nested.jpg",
    "diagram.svg",
    "report.html",       # in-paper sub-page report (host-less .html)
    "sub/page.html",
]


@pytest.mark.parametrize("value", UNTOUCHED)
def test_untouched(value: str) -> None:
    assert rewrite_link(ID, value) == value


@pytest.mark.parametrize("value,expected", ABSOLUTISED)
def test_absolutised(value: str, expected: str) -> None:
    assert rewrite_link(ID, value) == expected


@pytest.mark.parametrize("value", PREFIXED)
def test_prefixed(value: str) -> None:
    assert rewrite_link(ID, value) == f"{ID}/{value}"


def test_normalize_html_file_roundtrip() -> None:
    html = (
        '<link rel="stylesheet" href="/static/browse/0.3.4/css/x.css">'
        '<img src="Plots/fig.png">'
        '<a href="10.1038/30918">doi</a>'
        '<a href="www.sdss5.org">site</a>'
        '<a href="example.com/logo.png">3rd-party image link</a>'
        '<a href="mailto:a@b.org">mail</a>'
        '<a href="#S1">sec</a>'
    )
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "paper.html"
        p.write_text(html)
        normalize_html_links(ID, str(p))
        out = p.read_text()
    assert 'href="/static/browse/0.3.4/css/x.css"' in out        # root-relative untouched
    assert f'src="{ID}/Plots/fig.png"' in out                    # in-paper figure prefixed
    assert 'href="https://doi.org/10.1038/30918"' in out         # bare DOI absolutised
    assert 'href="https://www.sdss5.org"' in out                 # bare host absolutised
    assert 'href="https://example.com/logo.png"' in out          # 3rd-party servable-ext -> off arXiv
    assert 'href="mailto:a@b.org"' in out                        # scheme kept
    assert 'href="#S1"' in out                                   # fragment untouched
    assert f'{ID}/10.1038' not in out and f'{ID}/example.com' not in out  # never prefixed off-site
