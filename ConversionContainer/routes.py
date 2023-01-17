import flask
from flask import Flask, request, jsonify
from processing import process
from datetime import datetime
import os
from threading import Thread

app = Flask(__name__)

@app.route('/process', methods=['POST'])
def main ():
    print (request.json)
    thread = Thread(target = process, args = (request.json, ))
    thread.start()
    return '', 202

@app.route('/health', methods=['GET'])
def health():
    # Ask about LaTeXML status
    data = {   
        "time": datetime.now(),
        "CLOUD_RUN_TASK_INDEX": list(os.environ.items())
    }
    print (data)
    return jsonify(data), 200
    