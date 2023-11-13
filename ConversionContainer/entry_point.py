"""Initializes the Flask app"""
from source.factory import create_web_app
from source.models.util import create_all, drop_all, transaction
from google.cloud import logging

logging_client = logging.Client()
logging_client.setup_logging()

app = create_web_app()
# with app.app_context():
#     with transaction():
#         create_all() # Create table if it doesn't exist

if __name__=='__main__':
    app.run(debug=False)
