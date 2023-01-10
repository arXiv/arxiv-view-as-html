import functions_framework
import requests

@functions_framework.http
def get_html (request):
    # TODO:
    # Authenticate against replica DB
    # Serve rendered html to client
    pass

"""
(Ryan) Authorize users uploading in the first cloud function

XXX Stream instead of try to download whole thing (in conversion container get_file method)

XXX Write the dockerfile for Conversion Container

XXX Change environment variable to config file

XXX Download Deyan's css file and include in dockerfile

Write download container/flask server + authorize

Authorization Process:
- user id and stuff is in attached session cookie
- submission id will also be in request
- check that user id == submission's submitter id
- proceed
"""