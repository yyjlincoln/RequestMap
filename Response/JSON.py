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

    def convertDictionaryResponse(self, response, *, protocolName=None):
        if protocolName == 'HTTPViaFlask':
            return jsonify(response)
        elif protocolName == 'HTTPBatchRequestViaFlask':
            return response  # Do not convert to JSON for batch requests
        elif protocolName == 'HTTPRequestByEndpointIdentifier':
            return response
        else:
            return json.dumps(response)

    def standardizeResponse(self, code, message=None, *, protocolName=None, **kw):
        res = {
            'message': message if message else self.standardMessages.get(code, None),
            'code': code,
            **kw
        }
        return self.convertDictionaryResponse(res, protocolName=protocolName)

    def exceptionHandler(self, exception, *, protocolName=None):
        code = getattr(exception, 'code', -1)
        message = getattr(exception, 'message', None)
        if not message:
            message = self.standardMessages[code] if code in self.standardMessages else str(
                exception)

        res = {
            'code': code,
            'message': message,
            'exception': str(exception)
        }
        return self.convertDictionaryResponse(res, protocolName=protocolName)
