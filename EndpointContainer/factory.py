from flask import Flask

from arxiv_auth import auth

from arxiv_auth.auth.middleware import AuthMiddleware
from arxiv.base.middleware import wrap



def create_web_app() -> Flask:
    app = Flask(__name__)
    app.config.from_pyfile('config.py')

    # set the absolute path to the static folder
    app.static_folder = app.root_path + app.config.get('STATIC_FOLDER')
    app.template_folder = app.root_path + app.config.get('TEMPLATE_FOLDER')

    app.config['SERVER_NAME'] = None

    auth.Auth(app)
    wrap(app, [AuthMiddleware])
    
    return app
