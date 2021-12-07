class MissingParameter(Exception):
    def __init__(self, name):
        super().__init__(f"Missing parameter: {name}")
        self.name = name


class ParameterConversionFailure(Exception):
    def __init__(self, name):
        super().__init__(
            f"Parameter {name} can not be converted to the required type")
        self.name = name


class EndpointNotFound(Exception):
    def __init__(self, name):
        super().__init__(f"Endpoint {name} can not be found")
        self.name = name


class ValidationError(Exception):
    def __init__(self, code, message):
        self.message = message
        self.code = code
        super().__init__(message + ' (' + str(code) + ')')
