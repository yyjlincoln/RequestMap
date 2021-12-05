class StandardResponseHandler():
    def __init__(self) -> None:
        pass

    def standardizeResponse(self, protocolName, code, message='', **kw):
        raise NotImplementedError()

    def exceptionHandler(self, protocolName, exception):
        raise NotImplementedError()
    

class NoResponseHandler(StandardResponseHandler):
    def __init__(self) -> None:
        pass

    def standardizeResponse(self, protocolName, data):
        return data

    def exceptionHandler(self, protocolName, exception):
        return str(exception)
    
