class StandardResponseHandler():
    def __init__(self) -> None:
        pass

    def standardizeResponse(self, code, message='', *, protocol=None,  **kw):
        raise NotImplementedError()

    def exceptionHandler(self, exception, *, protocol=None):
        raise NotImplementedError()


class NoResponseHandler(StandardResponseHandler):
    def __init__(self) -> None:
        pass

    def standardizeResponse(self, data, *, protocol=None):
        return data

    def exceptionHandler(self, exception, *, protocol=None):
        return str(exception)
