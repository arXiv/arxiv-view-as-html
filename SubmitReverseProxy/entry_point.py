import sys
import ReverseProxy.files
sys.modules["arxiv.files"] = ReverseProxy.files
from ReverseProxy.factory import create_web_app

app = create_web_app()

if __name__=='__main__':
    app.run(debug=False)
