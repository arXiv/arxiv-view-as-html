"""Initializes the Flask app"""
from factory import create_web_app
from models.util import create_all

app = create_web_app()
with app.app_context():
    create_all() # Create table if it doesn't exist

if __name__=='__main__':
    app.run(debug=False)
