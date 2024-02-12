"""Initializes the Flask app"""
import logging

from google.cloud import logging as gcp_logging

from source.factory import create_web_app
from source.models.db import db


logger = logging.getLogger(__name__)
logger.basicConfig(level=logging.ERROR, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logging_client = gcp_logging.Client()
logging_client.setup_logging()

app = create_web_app()

@app.teardown_appcontext
def shutdown_session(exception = None):
    db.session.remove()

if __name__=='__main__':
    app.run(debug=False)
