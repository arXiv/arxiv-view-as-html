from flask import Flask
import markupsafe

from arxiv_auth import auth
from arxiv_auth.auth.middleware import AuthMiddleware
from arxiv.base.middleware import wrap

import google.cloud.logging

from .routes import blueprint

google.cloud.logging.Client().setup_logging()

def create_web_app() -> Flask:
    """
    Creates the Flask app

    Returns
    -------
    Flask
        Flask web app
    """

    app = Flask(__name__, static_folder=None)
    app.config.from_pyfile('config.py')
    app.config['SERVER_NAME'] = None

    app.register_blueprint(blueprint)

    # include_raw jinja loader used in template.html
    # app.jinja_env.globals['include_raw'] = lambda html_path : \
    #     markupsafe.Markup(app.jinja_loader.get_source(app.jinja_env, html_path)[0])
    
    auth.Auth(app)
    wrap(app, [AuthMiddleware])

    return app
