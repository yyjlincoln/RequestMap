class Standardizer():
    def standardizeResponse(self, protocolName, code, message='', **kw):
        raise NotImplementedError()

    def exceptionHandler(self, protocolName, exception):
        raise NotImplementedError()
