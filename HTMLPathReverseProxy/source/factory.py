from flask import Flask

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

    return app
