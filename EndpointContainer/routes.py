"""HTTPS routes for the Flask app"""
import logging
from functools import wraps
import datetime as dt
import shutil
from typing import Any, Callable, Optional
import os
import datetime
import config
from util import get_file, get_log, untar, inject_base_tag
import exceptions
from bs4 import BeautifulSoup, Tag
import google.cloud.logging
from google.cloud import storage
import google.auth
from google.auth.transport import requests
from authorize import authorize_user_for_submission, submission_published
from arxiv_auth.domain import Session
from flask import request, Blueprint, jsonify, render_template, current_app
from flask_cors import cross_origin

lclient = google.cloud.logging.Client()
lclient.setup_logging()
blueprint = Blueprint('routes', __name__, '')

def _get_google_auth () -> tuple[google.auth.credentials.Credentials, str, storage.Client]:
    credentials, project_id = google.auth.default()
    return (credentials, project_id, storage.Client(credentials=credentials))

def _get_auth(req: Any) -> Optional[Session]:
    logging.info("request: %s", 'None' if request is None else 'Not None')
    logging.info("hasattr(request, 'auth'): {%s}", 'True' if hasattr(request, 'auth') else 'False')
    if request and hasattr(request, 'auth') and request.auth:
        return req.auth
    else:
        return None

def _get_url(blob_name: Any) -> str:
    credentials, _, client = _get_google_auth()
    grequest = requests.Request()
    credentials.refresh(grequest)
    bucket = client.bucket(current_app.config['SOURCE_BUCKET'])
    blob = bucket.blob(blob_name)
    # """Generates a v4 signed URL for uploading a blob using HTTP PUT.
    url = blob.generate_signed_url(
        version="v4",
        # This URL is valid for 10 minutes
        expiration=datetime.timedelta(minutes=10),
        # Allow PUT requests using this URL.
        method="PUT",
        # Use updated credentials (new token for signature is created by Google every 12 hours)
        service_account_email=credentials.service_account_email,
        access_token=credentials.token,
    )
    return url

def authorize_for_submission(func: Callable) -> Callable:
    """
    Decorator that checks if the targeted submission is valid for the wrapped function.
    Needs to come before the @blueprint.route decorator.

    Parameters
    ----------
    func : Callable
        Some function call that might include a submission as an arg

    Returns
    -------
    Callable
        Function that has valid submission arg or no submission arg
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        try:
            if request and 'submission_id' in request.args and submission_published(request.args.get('submission_id')):
                # logging.info(f"Submission {request.args['submission_id']} authorized because it's already published")
                logging.info("Submission %s authorized because it's already published",
                    request.args['submission_id'])
                return func(*args, **kwargs)
            logging.info("Submission is not published (try)")
        except (exceptions.DBConnectionError, exceptions.DBConfigError) as exc:
            print(exc)
            # What to do if DB isn't configured?
        auth = _get_auth(request)
        try:
            if (auth and auth.user and ('submission_id' in request.args)
                and authorize_user_for_submission(auth.user.user_id, request.args.get('submission_id'))):
                logging.info("Submission %s authorized for user %s because they are the submitter",
                    request.args['submission_id'],
                    auth.user.user_id)
                return func(*args, **kwargs)
            else:
                return jsonify ({"message": "You don't have permission to view this resource"}), 404 # do make_response
        except Exception as e:
            logging.info(str(e))
            logging.info("user denied")
            return jsonify ({"message": "You don't have permission to view this resource"}), 404 # do make_response
    return wrapper

@blueprint.route('/download', methods=['GET'])
@cross_origin(supports_credentials=True)
@authorize_for_submission
def download():
    """
    Downloads the targeted article via arxiv_id or submission_id (prioritizes arxiv_id) in html format
    and processes it by adding base tags for static assets.

    Returns
    -------
    _type_
        Renders the article in html format.
    """
    logging.info("Logging works in routes.py file")
    _, _, client = _get_google_auth()
    blob_name = request.args.get('arxiv_id') or request.args.get('submission_id')
    print(f"request blob name is {blob_name}")
    if blob_name is None:
        return render_template("400.html", error = exceptions.PayloadError("Missing arxiv or submission id"))
        # Malformed request with no ID
    try:
        tar = get_file(
            current_app.config[
                'CONVERTED_BUCKET_ARXIV_ID' if request.args.get('arxiv_id')
                else 'CONVERTED_BUCKET_SUB_ID'],
            blob_name,
            client)
        source = untar(tar, blob_name)
    except exceptions.GCPBlobError as exc:
        logging.info("Download failed due to %s", exc)
        try:
            logpath = get_log(config.QA_BUCKET_NAME, blob_name, client)
            with open(logpath, "r") as f:
                log = f.read()
            return render_template("404.html", error = exc, log = log)
            # No HTML found, conversion log file found
        except Exception as e:
            return render_template("500.html", error = e)
            # No HTML or conversion log file found
    except Exception as exc:
        return render_template("500.html", error = exc)
        # File download or untarring went wrong
    inject_base_tag(source, f"/conversion/templates/{blob_name.replace('.', '-')}/html/")
    # This corrects the paths for static assets in the html
    return render_template("html_template.html", html=source)

@blueprint.route('/test404', methods=['GET'])
def test404():
    _, _, client = _get_google_auth()
    blob_name = '3966965_stdout.txt'
    blob_dir = "/source/errors/"
    bucket_name = config.QA_BUCKET_NAME
    try:
        os.makedirs(blob_dir)
    except Exception as exc:
        print(exc)
        print(f"Directory {blob_dir} already exists, remaking directory")
        shutil.rmtree(blob_dir)
        os.makedirs(blob_dir)
    try:
        blob = client.bucket(bucket_name).blob(blob_name)
        blob.download_to_filename(f"/source/errors/{blob_name}")
    except Exception as exc:
        raise exceptions.GCPBlobError(f"Download of {blob_name} from {bucket_name} failed") from exc
    with open(f"/source/errors/{blob_name}", "r") as f:
        log = f.read()
    return render_template("404.html", error = exceptions.GCPBlobError("404 Description"), log = log)

@blueprint.route('/test400', methods=['GET'])
def test400():
    return render_template("400.html", error = exceptions.GCPBlobError("400 Description"))

@blueprint.route('/test500', methods=['GET'])
def test500():
    return render_template("500.html", error = exceptions.GCPBlobError("500 Description"))

# add exception handling
@blueprint.route('/upload', methods=['POST'])
@cross_origin(supports_credentials=True)
@authorize_for_submission
def upload():
    """
    Generates the signed write url to upload the .tar.gz with the article to.

    Returns
    -------
    JSON
        JSON formatted string with the upload url for a particular article.
    """
    return jsonify({"url": _get_url(request.args.get('submission_id'))}), 200

@blueprint.route('/poll_submission', methods=['GET', 'OPTIONS'])
@cross_origin(supports_credentials=True)
@authorize_for_submission
def poll():
    """
    Checks if the container has GCP credentials and whether the article
    is already published (has arxiv id) or is in submission (has sub id only)

    Returns
    -------
    response
        {'exists': True if GCP valid and has an id}, 200
    """
    logging.info("CHECKING FOR AUTH IN POLL: %s", hasattr(request, 'auth'))
    try:
        _, _, client = _get_google_auth()
    except Exception:
        logging.critical("Failed to get GCP credentials or create storage client")
        return {'exists': False}, 500
    arxiv_id = request.args.get('arxiv_id')
    arxiv_conv_bucket = client.bucket(current_app.config['CONVERTED_BUCKET_ARXIV_ID'])
    if arxiv_id and arxiv_conv_bucket.blob(arxiv_id).exists():
        return {'exists': True}, 200
    submission_id = request.args.get('submission_id')
    sub_conv_bucket = client.bucket(current_app.config['CONVERTED_BUCKET_SUB_ID'])
    if submission_id and sub_conv_bucket.blob(submission_id).exists():
        return {'exists': True}, 200
    qa_bucket = client.bucket(current_app.config['QA_BUCKET_NAME'])
    if arxiv_id and qa_bucket.blob(arxiv_id + "_stdout.txt").exists():
        logblob = qa_bucket.get_blob(arxiv_id + "_stdout.txt")
        logblob.reload(client, 'full')
        if (dt.datetime.now(dt.timezone.utc) - logblob.time_created).total_seconds() > 90:
            return {'exists': True}, 200
    if submission_id and qa_bucket.blob(submission_id + "_stdout.txt").exists():
        logblob = qa_bucket.blob(submission_id + "_stdout.txt")
        logblob.reload(client, 'full')
        if (dt.datetime.now(dt.timezone.utc) - logblob.time_created).total_seconds() > 90:
            print(f"{submission_id} log found with no converted html")
            return {'exists': True}, 200
    return {'exists': False}, 200
        