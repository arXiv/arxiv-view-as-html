from flask import request, secure_filename, Blueprint, jsonify, render_template

from functools import wraps

from typing import Any, Callable

import config
from factory import create_web_app
from util import *
from authorize import authorize_user_for_submission

blueprint = Blueprint('routes', __name__, '')

def authorize_for_submission(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        if request.auth: # try hasattr(request, 'auth')
            if request.auth.user and ('submission_id' in request.form):
                if (authorize_user_for_submission(request.auth.user.user_id, request.form['submission_id'])):
                    return func(*args, **kwargs)
        return jsonify ({"message": "You don't have permission to view this resource"}), 403
    return wrapper

@blueprint.route('/download', methods=['GET'])
@authorize_for_submission
def download ():
    # Decrypt
    # DB Query
    # Authorize
    # Then...
    tar = get_file()
    source = untar(tar)
    return render_template()


@blueprint.route('/upload', methods=['POST'])
@authorize_for_submission
def upload ():
    pass
    # Do security things
    # We give them a signed write url
