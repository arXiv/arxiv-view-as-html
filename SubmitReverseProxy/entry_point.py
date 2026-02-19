import sys
import ReverseProxy.files
sys.modules["arxiv.files"] = ReverseProxy.files
from ReverseProxy.scaffold_response import browse_urls_fallback
from ReverseProxy.factory import create_web_app

app = create_web_app()

app.url_build_error_handlers.append(browse_urls_fallback)

if __name__=='__main__':
    app.run(debug=False)
