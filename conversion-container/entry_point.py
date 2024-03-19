"""Initializes the Flask app"""
import logging

from google.cloud import logging as gcp_logging

from conversion.factory import create_web_app

gcp_logging.Client().setup_logging()

app = create_web_app()

if __name__=='__main__':
    app.run(debug=False)
