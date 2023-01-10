import flask
from flask import Flask, request, secure_filename
from processing import process

app = Flask(__name__)

@app.route('/', methods=['POST'])
def main ():
    process(request.data)