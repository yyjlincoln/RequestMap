class StandardResponseHandler():
    def __init__(self) -> None:
        pass

    def standardizeResponse(self, code, message='', *, protocolName=None,  **kw):
        raise NotImplementedError()

    def exceptionHandler(self, exception, *, protocolName=None):
        raise NotImplementedError()


class NoResponseHandler(StandardResponseHandler):
    def __init__(self) -> None:
        pass

    def standardizeResponse(self, data, *, protocolName=None):
        return data

    def exceptionHandler(self, exception, *, protocolName=None):
        return str(exception)
