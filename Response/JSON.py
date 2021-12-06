import json
from .ResponseBase import StandardResponseHandler

# For Flask protocol only. This should be removed in the future and changed to Flask.addRule(...)
from flask import jsonify

STANDARD_MESSAGES = {
    0: "The request was successful",
    -1: "The request was unsuccessful",
}


class JSONStandardizer(StandardResponseHandler):
    def standardizeResponse(self, code, message=None, *, protocolName=None, **kw):
        res = {
            'message': message if message else STANDARD_MESSAGES.get(code, None),
            'code': code,
            **kw
        }
        if protocolName == 'HTTPViaFlask':
            return jsonify(res)
        else:
            return json.dumps(res)

    def exceptionHandler(self, exception, *, protocolName=None):
        res = {
            'code': getattr(exception, 'code', -1),
            'message': getattr(exception, 'message', str(exception)),
        }
        if protocolName == 'HTTPViaFlask':
            return jsonify(res)
        else:
            return json.dumps(res)
