from flask import Flask
from routes import blueprint
from models.util import init_app

def create_web_app(config_path: str=None) -> Flask:
    """
    Creates the Flask app with config at config_path.

    Parameters
    ----------
    config_path : str, optional
        Path to config.py file, by default None

    Returns
    -------
    Flask
        Flask web app
    """
    app = Flask(__name__)
    if config_path:
        app.config.from_pyfile(config_path)
    else:
        app.config.from_pyfile('config.py')
    
    app.register_blueprint(blueprint)

    init_app(app)

    return app
