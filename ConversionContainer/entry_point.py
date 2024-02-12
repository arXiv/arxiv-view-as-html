"""Initializes the Flask app"""
import logging

from source.factory import create_web_app
from source.models.db import db

logging.basicConfig(level=logging.ERROR, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = create_web_app()

@app.teardown_appcontext
def shutdown_session(exception = None):
    db.session.remove()

if __name__=='__main__':
    app.run(debug=False)
