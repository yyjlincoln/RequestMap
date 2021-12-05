class StandardResponseHandler():
    def __init__(self) -> None:
        pass

    def standardizeResponse(self, code, message = '', **kw):
        raise NotImplementedError()

    def exceptionHandler(self, exception):
        raise NotImplementedError()