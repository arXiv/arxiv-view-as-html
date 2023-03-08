from flask import Flask

from arxiv_auth import auth

from arxiv_auth.auth.middleware import AuthMiddleware
from arxiv.base.middleware import wrap

import os

import logging

import routes

from jinja2.utils import markupsafe

import google.cloud.logging
client = google.cloud.logging.Client()
client.setup_logging()

# This function is a jinja plugin that stops jinja from
# trying to parse jinja syntax in a block. It can be called
# from any template by typing:
# {{ include_raw ('path_to_html.html') }}
def include_raw (app: Flask, html_path: str):
    return markupsafe.Markup(app.jinja_loader.get_source(app.jinja_env, html_path)[0])

def create_web_app(config_path: str=None) -> Flask:
    app = Flask(__name__)
    if config_path:
        app.config.from_pyfile(config_path)
    else:
        app.config.from_pyfile('config.py')

    # Add the include_raw function to the jinja environment
    app.jinja_env.globals['include_raw'] = lambda html_path : include_raw(app, html_path)
    app.static_folder = app.template_folder
    app.config['SERVER_NAME'] = None
    app.register_blueprint(routes.blueprint)
    auth.Auth(app)
    wrap(app, [AuthMiddleware])
    
    return app
