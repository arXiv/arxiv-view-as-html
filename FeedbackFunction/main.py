import functions_framework
from models import add_feedback

def _validate_params (params, field_names) -> bool:
    for field in field_names:
        if field not in params:
            return False
    return True

@functions_framework.http
def main(request):
    """HTTP Cloud Function.
    Args:
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
        'locationHigh'
    ]

    if _validate_params (request.args, field_names):
        add_feedback(
            request.args['uniqueId'],
            request.args['canonicalURL'],
            request.args['conversionURL'],
            request.args['reportTime'],
            request.args['browserInfo'],
            request.args['locationLow'],
            request.args['locationHigh'],
            request.args['description']
        )
        return '', 200
    return '', 400

