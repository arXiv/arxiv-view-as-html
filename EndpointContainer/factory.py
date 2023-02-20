from flask import Flask

from arxiv_auth import auth

from arxiv_auth.auth.middleware import AuthMiddleware
from arxiv.base.middleware import wrap

import os

import logging

import routes

import google.cloud.logging
client = google.cloud.logging.Client()
client.setup_logging()

def list_files(startpath):
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        logging.info('{}{}/'.format(indent, os.path.basename(root)))
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            logging.info('{}{}'.format(subindent, f))

def create_web_app(config_path: str=None) -> Flask:
    app = Flask(__name__)
    if config_path:
        app.config.from_pyfile(config_path)
    else:
        app.config.from_pyfile('config.py')

    # set the absolute path to the static folder
    app.static_folder = app.root_path + app.config.get('STATIC_FOLDER')
    template_folder = os.path.join(app.root_path, 'templates')
    os.makedirs(template_folder)
    app.template_folder = template_folder 
    # app.root_path + app.config.get('TEMPLATE_FOLDER')
    logging.info(app.template_folder)

    app.config['SERVER_NAME'] = None

    app.register_blueprint(routes.blueprint)

    auth.Auth(app)
    wrap(app, [AuthMiddleware])
    
    return app
