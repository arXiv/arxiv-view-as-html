import sys
import ReverseProxy.files
# We are making a pragmatic trade-off here:
# We continue to rely on `arxiv-auth` using a now dated version of `arxiv-base`.
# However, we need the file transforms from the most recent `arxiv-base` to support 
# the jinja template scaffold over HTML papers.
#
# Hence, introduce `arxiv.files` via a manual module declaration, fully expecting that 
# this entire reverse proxy service will be obsoleted by moving the Submission system to the cloud.
# If we ever need to adapt this in the future (e.g. adding more recent `arxiv-base` features),
# we should bite the bullet and remove `arixv-auth`, upgrading to the latest auth from base.
#
# ruff: noqa: E402
sys.modules["arxiv.files"] = ReverseProxy.files 
from ReverseProxy.scaffold_response import register_scaffold_urls
from ReverseProxy.factory import create_web_app

app = create_web_app()

# tests/scaffold_smoke.py wires a bare app the same way, so keep this a single call.
register_scaffold_urls(app)

if __name__=='__main__':
    app.run(debug=False)
