import logging
import sys
from typing import Optional, Dict

from flask import Flask

from .config import Settings
from .routes import blueprint

def create_web_app(**kwargs) -> Flask:
    """
    Creates the Flask app with config at config_path.

    Parameters
    ----------
    config : Dict, optional
        config dictionary

    Returns
    -------
    Flask
        Flask web app
    """
    settings = Settings(**kwargs)

    app = Flask(__name__)

    app.config.from_object(settings)
   
    app.register_blueprint(blueprint)

    return app
