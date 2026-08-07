import logging
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from bs4 import BeautifulSoup
from flask import current_app

from ...domain.conversion import ConversionPayload, LaTeXMLOutput
from ..files import get_file_manager

MISSING_PACKAGE_RE = re.compile(
    r"^Warning:missing_file:(\S+)\s(?:Can't\sfind\s(package|binding for class))?", flags=re.MULTILINE
)
TMPDIR = Path(os.getenv("TMPDIR", "/tmp"))
UID = os.getuid()


def format_missing_dependency(name: str, message_fragment: str) -> str | None:
    if name.endswith((".sty", ".cls")):
        return name
    # Ignore some common low-level issues, this report focuses on the high-level latexml requirements
    elif name.endswith((".css", ".js", ".tex", ".ltx", ".def")):
        return None
    else:
        ext = "cls" if message_fragment == "binding for class" else "sty"
        return f"{name}.{ext}"


def list_missing_packages(latexml_log_path: Path) -> list[str]:
    matches = []
    if latexml_log_path.exists():
        with open(latexml_log_path) as latexml_log_stream:
            for line in latexml_log_stream:
                match = re.search(MISSING_PACKAGE_RE, line)
                if match:
                    matches.append(match)
    return list(filter(None, map(lambda match: format_missing_dependency(match[1], match[2]), matches)))


def clean_up_stale_assets(tmpdir: Path, stale_asset_expiration_sec: int) -> None:
    """
    Clean the temporary directory from all files that have are now stale (too old).

    When latexml dies in particularly dirty ways (e.g. imagemagick issues) the initial
    web service process may become completely unrecoverable. In these cases files can remain
    in the temporary directory for an indefinite amount of time, and fill up the disk.
    """
    now = time.time()
    # Always try to clean up old / unneeded files.
    for entry in os.listdir(tmpdir):
        # exempt the cloudsql file, if it exists, we want to allow its reuse
        if entry.endswith("csql"):
            continue
        full_entry = os.path.join(tmpdir, entry)
        try:
            stat = os.stat(full_entry)
        except FileNotFoundError:
            continue  # likely got cleaned up in parallel
        # only consider old files this user owns.
        age = now - stat.st_mtime
        if stat.st_uid == UID and (age > stale_asset_expiration_sec):
            logging.warning(f"deleting stale temporary asset ({age}s): {full_entry}")
            try:
                if os.path.isfile(full_entry):
                    os.remove(full_entry)
                else:
                    shutil.rmtree(full_entry)
            except Exception as e:
                logging.error(f"failed to delete stale temporary asset: {full_entry} ({e})")


def latexml(payload: ConversionPayload, workdir: Path) -> LaTeXMLOutput:
    LATEXML_URL_BASE = current_app.config.get("LATEXML_URL_BASE", "")
    assert LATEXML_URL_BASE.startswith("/") or LATEXML_URL_BASE.startswith("http"), \
        f"The base URL '{LATEXML_URL_BASE}' needs to be either absolute or relative to root, or it will get rewritten"
    # latexml-oxide compiles the ar5iv/arXiv bindings into the binary, so the
    # external ar5iv-bindings tree (and its --path entries) is no longer needed;
    # default to no extra search paths. Config may still supply some if required.
    LATEXML_PATHS = current_app.config.get("LATEXML_PATHS", [])
    # Note that the ar5iv.sty preload activates the bundled ar5iv profile, which touches up the
    # produced HTML output for a typical arXiv article, as well as adds typical resource limits
    # internal to the conversion pass.
    LATEXML_PRELOADS = current_app.config.get("LATEXML_PRELOADS", ["ar5iv.sty"])
    LATEXML_LOG_FILE = current_app.config.get("LATEXML_LOG_FILE", "__stdout.txt")
    LATEXML_TIMEOUT_SEC = int(current_app.config.get("LATEXML_TIMEOUT_SEC", 180))
    LATEXML_MEM_LIMIT_BYTES = int(current_app.config.get("LATEXML_MEM_LIMIT_BYTES", 6 * 1024**3))
    # Always clean up before executing the latexml call, this is too important
    # for service health, so we tightly couple it with this call.
    # (at least for now)
    #
    # Assets are considered stale 5 min after a fully timed latexml run is over.
    stale_asset_expiration_sec = 300 + LATEXML_TIMEOUT_SEC
    clean_up_stale_assets(TMPDIR, stale_asset_expiration_sec)

    output_dirname = get_file_manager().latexml_output_dir_name(payload)
    output_path = f"{output_dirname}{payload.name}.html"
    log_path = f"{output_dirname}{LATEXML_LOG_FILE}"

    latexml_config = [
        "latexml_oxide",
        "--whatsin=directory",
        "--pmml",
        "--mathtex",
        "--noinvisibletimes",
        "--format=html5",
        "--navigationtoc=context",
        # latexml-oxide ships built-in default CSS/JS; suppress them so the arXiv
        # ar5iv assets linked below are the only stylesheets/scripts referenced.
        "--nodefaultresources",
        f"--timeout={LATEXML_TIMEOUT_SEC}",
        # Native memory budget (MiB): the engine spills completed subtrees to
        # TMPDIR as it approaches the ceiling, then a watchdog aborts (exit 137)
        # at it. Replaces the previous external `prlimit --as` address-space cap.
        f"--max-memory={LATEXML_MEM_LIMIT_BYTES // 1024**2}",
        f"--css={LATEXML_URL_BASE}/css/arxiv-html-papers-20260807.css",
        f"--javascript={LATEXML_URL_BASE}/js/arxiv-html-papers-20260131.js",
        f"--source={workdir}",
        f"--log={log_path}",
        f"--dest={output_path}",
    ]
    for preload in LATEXML_PRELOADS:
        latexml_config.append(f"--preload={preload}")
    for path in LATEXML_PATHS:
        latexml_config.append(f"--path={path}")
    try:
        completed_process = subprocess.run(
            latexml_config,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
            timeout=LATEXML_TIMEOUT_SEC + 5,
        )
        returncode = completed_process.returncode
        if returncode != 0:
            logging.error(
                f"LaTeXML conversion failed rc={returncode} "
                f"(mem_limit={LATEXML_MEM_LIMIT_BYTES}) for {payload.identifier}"
            )
    except subprocess.TimeoutExpired as e:
        logging.warning(f"LaTeXML conversion timed out after {e.timeout} seconds")
        returncode = 1
    except Exception as e:
        logging.warning(f"LaTeXML conversion failed with error {e}")
        returncode = 1
    # Note: latexml will write the full conversion log at the path specified by `--log=[path]`,
    # so we can keep the current __stdout.txt convention for now by copying the deposited log.
    return LaTeXMLOutput(
        missing_packages=list_missing_packages(Path(log_path)),
        log=None,  # use the file from --log
        returncode=returncode,
    )

# The only relative resources arXiv actually serves under /html/<id>/. A
# HOST-LESS reference ending in one of these is an in-paper asset and gets the
# paper-id prefix; every other scheme-less reference is pushed to an absolute
# off-arXiv https:// URL instead of a /html/<id>/ path that would 404 and feed
# the crawler/SEO damage in arXiv/html_feedback#6854. `html` is kept for in-paper
# sub-page reports -- the host check below is what stops a third-party
# `www.foo.com/page.html` / `example.com/logo.png` being tangled in as a local one.
LOCAL_FILE_EXTENSIONS = {"css", "js", "png", "jpg", "jpeg", "gif", "svg", "html"}
LINK_ATTR_REGEX = re.compile(r'\b(href|src|data)\s*=\s*"([^"]*)"', re.IGNORECASE)
URI_SCHEME_REGEX = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")
EMAIL_REGEX = re.compile(r"^[^\s/@]+@[^\s/@]+\.[A-Za-z]{2,}$")
DOI_REGEX = re.compile(r"^10\.\d{4,}/\S+$")
TLD_REGEX = re.compile(r"^[A-Za-z]{2,}$")


def _extension(value: str) -> str:
    """Lower-cased extension of the last path segment (before ? or #), or ''."""
    last = value.split("?", 1)[0].split("#", 1)[0].rsplit("/", 1)[-1]
    return last.rsplit(".", 1)[-1].lower() if "." in last else ""


def _looks_like_host(value: str) -> bool:
    """True if a scheme-less value names an external host (domain), not an in-paper path.

    ``www.foo``, ``example.com``, ``x.github.io/…`` are hosts; ``report.html``,
    ``x1.png``, ``figs/plot.svg``, ``section2`` are not. A servable-asset extension
    (png, html, …) as the last label of the first segment means a local file, not
    a TLD -- so it is never treated as a host.
    """
    first = value.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    if first.lower().startswith("www."):
        return True
    if "." not in first:
        return False
    tld = first.rsplit(".", 1)[-1].lower()
    if tld in LOCAL_FILE_EXTENSIONS or not TLD_REGEX.match(tld):
        return False
    return True


def rewrite_link(prefix: str, value: str) -> str:
    """Normalise a single href/src/data value from the converted HTML.

    Broken links are a real cost: scheme-less external references (bare DOIs,
    emails, `www.`/host URLs) resolve relative to the paper URL, so a link meant
    for ``https://doi.org/10.1038/30918`` is fetched as
    ``/html/<id>/10.1038/30918`` and 404s -- reader-visible breakage and large
    volumes of crawler 404s (arXiv/html_feedback#6854). So:

    - untouched: empty, fragment (``#``), root/query/protocol-relative
      (``/``, ``?``, ``//``), and anything already carrying a URI scheme
      (``https:``, ``mailto:``, ``ftp:``, ``tel:``, ``data:`` ...).
    - absolutised off arXiv (never prefixed): emails -> ``mailto:``, DOIs ->
      ``https://doi.org/``, hosts (``www.``/``domain.tld``) -> ``https://``, and
      any other host-less reference whose extension is not a servable in-paper
      asset (it would only 404 under /html/<id>/).
    - prefixed with ``<prefix>/``: only host-less references to a servable
      in-paper asset (:data:`LOCAL_FILE_EXTENSIONS`), which /html/<id>/ serves.
    """
    if not value or value[0] in "#/?":
        return value
    if URI_SCHEME_REGEX.match(value):
        return value
    if EMAIL_REGEX.match(value):
        return "mailto:" + value
    if DOI_REGEX.match(value):
        return "https://doi.org/" + value
    if _looks_like_host(value):
        return "https://" + value
    if _extension(value) in LOCAL_FILE_EXTENSIONS:
        return f"{prefix}/{value}"
    return "https://" + value


def normalize_html_links(prefix: str, html_file_path: str) -> None:
    """Rewrite every href/src/data link in an HTML file via :func:`rewrite_link`."""
    with open(html_file_path, "r+") as html:
        new_text = LINK_ATTR_REGEX.sub(
            lambda m: f'{m.group(1)}="{rewrite_link(prefix, m.group(2))}"',
            html.read(),
        )
        html.truncate(0)
        html.seek(0)
        html.write(new_text)
