class RequestMapException(Exception):
    '''The base exception class for all RequestMap exceptions'''
    pass


class MissingParameter(RequestMapException):
    def __init__(self, name):
        super().__init__(f"Missing parameter: {name}")
        self.name = name
        self.code = -10001


class ParameterConversionFailure(RequestMapException):
    def __init__(self, name):
        super().__init__(
            f"Parameter {name} can not be converted to the required type")
        self.name = name
        self.code = -10002


class EndpointNotFound(RequestMapException):
    def __init__(self, name):
        super().__init__(f"Endpoint {name} can not be found")
        self.name = name
        self.code = -10000


class ValidationError(RequestMapException):
    def __init__(self, code, message=None):
        self.message = message
        self.code = code
        if message:
            super().__init__(message + ' (' + str(code) + ')')
        else:
            super().__init__('ValidationError: ' + str(code))
