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
from arxiv.base.urls import register_external_urls
from ReverseProxy.scaffold_response import browse_urls_fallback
from ReverseProxy.factory import create_web_app

app = create_web_app()

# The vendored arxiv-base `base/footer.html` links to the info site via named endpoints
# (about, help, contact, ...) which only exist in arxiv-base's external URL map. This is the
# part of `Base(app)` we need; the rest of that blueprint is too old here to be worth wiring.
# It goes first so that `browse_urls_fallback` stays the handler of last resort, and can keep
# logging the endpoints that nothing at all could build.
register_external_urls(app)

app.url_build_error_handlers.append(browse_urls_fallback)

if __name__=='__main__':
    app.run(debug=False)
