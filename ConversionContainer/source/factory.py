import logging
import sys
from typing import Optional, Dict

from flask import Flask
from flask.logging import default_handler

from .routes import blueprint
from .models.util import init_app

def create_web_app(config: Optional[Dict]=None) -> Flask:
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
    app = Flask(__name__)

    main = logging.getLogger(__name__)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    main.addHandler(handler)

    if config:
        app.config.from_mapping(config)
    else:
        app.config.from_pyfile('config.py')
    
    app.register_blueprint(blueprint)

    init_app(app)

    return app
