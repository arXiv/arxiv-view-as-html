import flask
from flask import Flask, request, secure_filename
import config
from util import *
import datetime
from google.cloud import storage

app = Flask(__name__)

@app.route('/download', methods=['GET'])
def download ():
    # Decrypt
    # DB Query
    # Authorize
    # Then...
    get_file()

@app.route('/upload', methods=['POST'])
def upload (request):
    """Generates a v4 signed URL for uploading a blob using HTTP PUT.

    Note that this method requires a service account key file. You can not use
    this if you are using Application Default Credentials from Google Compute
    Engine or from the Google Cloud SDK.
    """
    bucket_name = 'latexml_submission_source'
    blob_name = request.auth.user + "_submission"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    url = blob.generate_signed_url(
        version="v4",
        # This URL is valid for 10 minutes
        expiration=datetime.timedelta(minutes=10),
        # Allow PUT requests using this URL.
        method="PUT",
    )

    # print("Generated PUT signed URL:")
    # print(url)
    # print("You can use this URL with any user agent, for example:")
    # print(
    #     "curl -X PUT -H 'Content-Type: application/octet-stream' "
    #     "--upload-file my-file '{}'".format(url)
    # )
    # The above snippet is how to use the URL
    # Needs to be sent to XML endpoint in 
    return url
    # Do security things
    # We give them a signed write url
