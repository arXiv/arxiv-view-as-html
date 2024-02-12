"""Initializes the Flask app"""
import logging

# from google.cloud import logging as gcp_logging

from source.factory import create_web_app
from source.models.db import db

app = create_web_app()

@app.teardown_appcontext
def shutdown_session(exception = None):
    db.session.remove()

if __name__=='__main__':
    app.run(debug=False)
