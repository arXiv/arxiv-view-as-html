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
    LATEXML_URL_BASE = current_app.config["LATEXML_URL_BASE"]
    LATEXML_PATHS = current_app.config.get(
        "LATEXML_PATHS",
        [
            "/opt/ar5iv-bindings/bindings",
            "/opt/ar5iv-bindings/supported_originals",
        ],
    )
    LATEXML_PRELOADS = current_app.config.get("LATEXML_PRELOADS", ["ar5iv.sty"])
    LATEXML_LOG_FILE = current_app.config.get("LATEXML_LOG_FILE", "__stdout.txt")
    LATEXML_TIMEOUT_SEC = int(current_app.config.get("LATEXML_TIMEOUT_SEC", 540))
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
        "latexmlc",
        "--preload=[nobibtex,nobreakuntex,rawstyles,magnify=1.2,zoomout=1.2,tokenlimit=249999999,iflimit=3599999,absorblimit=1299999,pushbacklimit=599999]latexml.sty",
        "--pmml",
        "--mathtex",
        "--noinvisibletimes",
        f"--timeout={LATEXML_TIMEOUT_SEC}",
        "--nodefaultresources",
        "--format=html5",
        f"--css={LATEXML_URL_BASE}/css/arxiv-html-papers-20250916.css",
        "--javascript=https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js",
        "--javascript=https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.3.3/html2canvas.min.js",
        f"--javascript={LATEXML_URL_BASE}/js/addons_new.js",
        f"--javascript={LATEXML_URL_BASE}/js/feedbackOverlay.js",
        "--navigationtoc=context",
        "--whatsin=directory",
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
            check=True,
            text=True,
            timeout=LATEXML_TIMEOUT_SEC + 5,
        )
        returncode = completed_process.returncode
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


def insert_base_tag(idv: str, html_file_path: str) -> None:
    """Insert the base tag into the html so we can use the /html/arxiv_id url."""
    base_html = f'<base href="/html/{idv}/">'

    with open(html_file_path, "r+") as html:
        soup = BeautifulSoup(html.read(), "html.parser")
        if soup.head:
            soup.head.append(BeautifulSoup(base_html, "html.parser"))
            html.truncate(0)
            html.seek(0)
            html.write(str(soup))


def replace_relative_anchors(absolute_base: str, html_file_path: str) -> None:
    """Replace all the relative anchor tags with absolute anchors."""
    # Note: If this causes bugs, use a SAX parser to do this more accurately
    # while still not needing to completely rebuild the DOM in memory with bs4
    ANCHOR_REGEX = re.compile(r'href="#')
    with open(html_file_path, "r+") as html:
        new_text = re.sub(ANCHOR_REGEX, f'href="{absolute_base}#', html.read())
        html.truncate(0)
        html.seek(0)
        html.write(new_text)
