class ValidationError(Exception):
    def __init__(self, code, message):
        self.message = message
        self.code = code
        super().__init__(message + ' (' + str(code) + ')')

class StandardValidator():
    def __init__(self):
        self.map = None
        self.name = None

    def install(self, map):
        self.map = map
        self.initialise()

    def initialise(self):
        pass

    def getEvaluationMethod(self, endpoint):
        '''
        Returns the evaluation method for the given endpoint.
        The return value is discarded. Throw an error if validation fails.
        Preferably the error should be an instance of ValidationError.
        '''
        def evaluate(sampleValidatorArgument):  # Put required/optional arguments here
            raise ValidationError(-400, 'Not implemented. Can not validate.')
        return evaluate

