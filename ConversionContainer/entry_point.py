"""Initializes the Flask app"""
from source.factory import create_web_app
from source.models.db import db
from google.cloud import logging

logging_client = logging.Client()
logging_client.setup_logging()

app = create_web_app()

@app.teardown_appcontext
def shutdown_session(exception = None):
    db.session.remove()

if __name__=='__main__':
    app.run(debug=False)
