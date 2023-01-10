import flask
from flask import Flask, request, secure_filename
import config
from util import *

app = Flask(__name__)

@app.route('/download', methods=['GET'])
def download ():
    # Decrypt
    # DB Query
    # Authorize
    # Then...
    get_file()

@app.route('/upload', methods=['POST'])
def upload ():
    pass
    # Do security things
    # We give them a signed write url
