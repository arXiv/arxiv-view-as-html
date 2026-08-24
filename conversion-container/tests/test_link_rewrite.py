"""Tests for HTML link normalisation (conversion.services.latexml.rewrite_link).

Guards against the broken-link class in arXiv/html_feedback#6854: scheme-less
external references (bare DOIs, emails, `www.`/host URLs) must be absolutised so
they never resolve under /html/<id>/ and 404. Only host-less references to a
servable in-paper asset get the paper-id prefix.
"""
import tempfile
from pathlib import Path

import pytest
from arxiv.identifier import Identifier

from conversion.services.latexml import (
    html_asset_prefix,
    normalize_html_links,
    rewrite_link,
)

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
    "/static/browse/0.3.4/css/arxiv-html-papers-20260823.css",
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
    "logo@2x.png",       # retina asset: email-shaped but a servable in-paper file
    "fig@3x.jpg",
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


# --- old-style ids: asset prefix must drop the archive ---------------------
#   Regression: /html/astro-ph/0303073v1 rendered but its figures 404'd. The
#   in-paper link prefix was the archive-qualified idv ("astro-ph/0303073v1"),
#   so "BBNfig1.png" -> "astro-ph/0303073v1/BBNfig1.png", which a browser
#   resolves relative to the page's parent (/html/astro-ph/) into the doubled
#   "/html/astro-ph/astro-ph/0303073v1/BBNfig1.png". The prefix must be the bare
#   version-qualified filename ("0303073v1"); new-style ids are unaffected.
@pytest.mark.parametrize(
    "idv,expected",
    [
        ("astro-ph/0303073v1", "0303073v1"),   # old-style: archive dropped
        ("hep-th/9711200v3", "9711200v3"),     # old-style, later version
        ("cond-mat/0102536v1", "0102536v1"),   # old-style, hyphenated archive
        ("2608.05281v1", "2608.05281v1"),      # new-style: unchanged (== idv)
    ],
)
def test_html_asset_prefix(idv: str, expected: str) -> None:
    assert html_asset_prefix(Identifier(idv)) == expected


def test_old_style_figure_link_resolves_under_html_id() -> None:
    """Old-style figure links must resolve under ``/html/<id>/``, not double the archive.

    After normalisation the link is ``<filename>v<ver>/<asset>`` -- which resolves
    to ``/html/<id>/<asset>`` -- and never re-introduces the archive (the
    doubled-``astro-ph`` 404).
    """
    arxiv_id = Identifier("astro-ph/0303073v1")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "paper.html"
        p.write_text('<img src="BBNfig1.png"><img src="figs/plot.png">')
        normalize_html_links(html_asset_prefix(arxiv_id), str(p))
        out = p.read_text()
    assert 'src="0303073v1/BBNfig1.png"' in out
    assert 'src="0303073v1/figs/plot.png"' in out
    assert "astro-ph" not in out  # archive must not leak into the relative link


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
