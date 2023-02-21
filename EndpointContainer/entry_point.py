from factory import create_web_app
from arxiv_auth.legacy.models import db

app = create_web_app()

if __name__=='__main__':
    app.run(debug=False)