import functions_framework
from models import add_feedback
import re

def _validate_params (params, field_names) -> bool:
    id_re = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$')
    if not (params.get('uniqueId') and re.match(id_re, params['uniqueId'])):
        return False
    for field in field_names:
        if field not in params:
            return False
    return True

@functions_framework.http
def main(request):
    """HTTP Cloud Function.
    form:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """

    field_names = [
        'uniqueId',
        'canonicalURL',
        'conversionURL',
        'reportTime',
        'browserInfo',
        'description',
        'locationLow',
        'locationHigh',
        'selectedHtml', 
        'initiationWay'
    ]

    if _validate_params (request.form, field_names):
        add_feedback(
            request.form['uniqueId'],
            request.form['canonicalURL'],
            request.form['conversionURL'],
            int(request.form['reportTime']),
            request.form['browserInfo'],
            request.form['locationLow'],
            request.form['locationHigh'],
            request.form['description'],
            request.form['selectedHtml'],
            request.form['initiationWay'],

        )
        return '', 200
    return '', 400

