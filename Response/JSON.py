class JSONResponseStandardizer():

    def standardizeResponse(self, code, message = '', **kw):
        raise NotImplementedError()

    def exceptionHandler(self, exception):
        raise NotImplementedError()