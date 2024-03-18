from typing import List
import re
import subprocess

from flask import current_app

from arxiv.files import LocalFileObj

from ..files import get_file_manager
from ...domain.conversion import ConversionPayload, LaTeXMLOutput

MISSING_PACKAGE_RE = re.compile(r"Warning:missing_file:.+Can't\sfind\spackage\s(.+)\sat")

def list_missing_packages (stdout: str) -> List[str]:
    matches = MISSING_PACKAGE_RE.finditer(stdout)
    return list(map(lambda x: x.group(1), matches))

def latexml(main_src: LocalFileObj, payload: ConversionPayload) -> LaTeXMLOutput:
    LATEXML_URL_BASE = current_app.config['LATEXML_URL_BASE']

    main_src_path = main_src.item
    output_path = f'{get_file_manager().latexml_output_dir(payload)}{payload.name}.html'

    latexml_config = ["latexmlc",
                      "--preload=[nobibtex,ids,localrawstyles,mathlexemes,magnify=2,zoomout=2,tokenlimit=99999999,iflimit=1499999,absorblimit=1299999,pushbacklimit=599999]latexml.sty",
                      "--path=/opt/arxmliv-bindings/bindings",
                      "--path=/opt/arxmliv-bindings/supported_originals",
                      "--pmml", "--cmml", "--mathtex",
                      "--timeout=500",
                      "--nodefaultresources",
                      "--css=https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css",
                      f"--css={LATEXML_URL_BASE}/css/ar5iv_0.7.4.min.css",
                      f"--css={LATEXML_URL_BASE}/css/latexml_styles.css",
                      "--javascript=https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js",
                      "--javascript=https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.3.3/html2canvas.min.js",
                      f"--javascript={LATEXML_URL_BASE}/js/addons.js",
                      f"--javascript={LATEXML_URL_BASE}/js/feedbackOverlay.js",
                      "--navigationtoc=context",
                      f"--source={main_src_path}", f"--dest={output_path}"]
    
    completed_process = subprocess.run(
        latexml_config,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
        text=True,
        timeout=500)
    
    return LaTeXMLOutput(
        output=completed_process.stdout,
        missing_packages=list_missing_packages(completed_process.stdout)
    )
    
