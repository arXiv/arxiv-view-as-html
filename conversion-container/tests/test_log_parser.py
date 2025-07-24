import os
import tempfile
from pathlib import Path

import pytest

from conversion.services.latexml import list_missing_packages


@pytest.mark.logparser_unit_tests
def test_find_package_and_class():
    latexml_log = b"""
Warning:missing_file:imsart Can't find binding for class imsart (using OmniBus)
Warning:missing_file:xifthen Can't find package xifthen
Warning:missing_file: fail.
Warning:missing_file:biblatex.sty biblatex.sty is only minimally stubbed and will not be interpreted raw.
Info:fallback:revtex4-2.cls Interpreted 4-2 as a versioned package/class name, falling back to generic revtex.cls
Warning:missing_file:/static/browse/0.3.4/css/ar5iv.0.7.9.min.css Couldn't find resource file...
Warning:missing_file:/static/browse/0.3.4/js/addons_new.js Couldn't find resource file...
"""
    log_tmpfile = tempfile.NamedTemporaryFile(delete=False)
    log_tmpfile.write(latexml_log)
    log_tmpfile.close()
    missing_packages = list_missing_packages(Path(log_tmpfile.name))
    os.remove(log_tmpfile.name)
    assert missing_packages == [
        "imsart.cls",
        "xifthen.sty",
        "biblatex.sty",
    ], "Failed to correctly extract missing package/class name"
