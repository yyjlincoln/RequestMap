import json
from .ResponseBase import StandardResponseHandler

# For Flask protocol only. This should be removed in the future and changed to Flask.addRule(...)
from flask import jsonify


class JSONStandardizer(StandardResponseHandler):
    def __init__(self, standardMessages: dict = {
        0: "The request was successful",
        -1: "The request was unsuccessful",
    }) -> None:
        super().__init__()
        self.standardMessages = standardMessages

    def standardizeResponse(self, code, message=None, *, protocolName=None, **kw):
        res = {
            'message': message if message else self.standardMessages.get(code, None),
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
