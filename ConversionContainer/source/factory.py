from typing import Optional, Dict
from flask import Flask
from .routes import blueprint
from .models.util import init_app

def create_web_app(config: Optional[Dict]=None) -> Flask:
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
    if config:
        app.config.from_mapping(config)
    else:
        app.config.from_pyfile('config.py')
    
    app.register_blueprint(blueprint)

    init_app(app)

    return app
