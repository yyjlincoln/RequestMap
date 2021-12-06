from functools import wraps
import inspect
from typing import Any, Callable

from .Response.ResponseBase import NoResponseHandler, StandardResponseHandler
from .Protocols.ProtocolBase import StandardProtocolHandler
from .Validators.ValidatorBase import StandardValidator

import time


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


class ValidationFailure(Exception):
    def __init__(self, message):
        super().__init__(message)


class JITDict(dict):
    '''
    Just-in-time dictionary
    - fetches the key from getData in real time
    - stores a copy of any changes
    - returns None if a key does not exist
    '''

    def __init__(self, getData: Callable, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.getData = getData

    def __getitem__(self, key: str) -> Any:
        if super().__contains__(key):
            return super().__getitem__(key)
        else:
            return self.getData(key)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)

    def __contains__(self, __o: object) -> bool:
        sup = super().__contains__(__o)
        if not sup:
            return self.getData(__o) != None
        return True


class Map():
    def __init__(self) -> None:
        'Note: DataName of \'makeResponse\' is reserved for the response handler'
        self.endpointMap = {}
        self.installedProtocols = []
        self.installedResponseHandler = NoResponseHandler()
        self.installedValidators = []

    def analyseParameters(self, func):
        parameters = inspect.signature(func).parameters
        varKeyword = None
        nonOptionalParameters = []
        optionalParameters = {}

        for name, parameter in parameters.items():
            if parameter.kind == inspect.Parameter.POSITIONAL_ONLY:
                raise Exception(
                    "Positional-only parameters are not supported. All parameters must be named and must not be positional-only.")
            elif parameter.kind == inspect.Parameter.VAR_POSITIONAL:
                raise Exception(
                    "Var-positional parameters are not supported. All parameters must be named and must not be positional-only.")
            elif parameter.kind == inspect.Parameter.VAR_KEYWORD:
                varKeyword = parameter.name
            else:
                if parameter.default != inspect.Parameter.empty:
                    optionalParameters[name] = parameter.default
                else:
                    nonOptionalParameters.append(name)
        return varKeyword, nonOptionalParameters, optionalParameters

    def getCallDict(self, getData: Callable, varKeyword: str = None, nonOptionalParameters: list = [], optionalParameters: dict = {}, dataConverters: dict = {}) -> dict:
        # Check if all required parameters are present
        callDict = {}

        for parameter in nonOptionalParameters:
            data = getData(parameter)
            if data == None:
                raise MissingParameter(parameter)
            else:
                callDict[parameter] = data

        # Add optional parameters
        for parameter in optionalParameters:
            data = getData(parameter)
            if data != None:
                callDict[parameter] = data

        # Convert Parameters
        for parameter in dataConverters:
            if parameter in callDict:
                try:
                    callDict[parameter] = dataConverters[parameter](
                        callDict[parameter])
                except:
                    raise ParameterConversionFailure(parameter)

        if varKeyword != None:
            callDict[varKeyword] = JITDict(getData)

        return callDict

    def register(self, endpointHandler: str, endpointIdentifier: str, metadata: dict = {}, **dataConverters: dict) -> None:
        '''
        Register a new endpoint.
        :param endpointHandler: The endpoint handler function.
        :param endpointIdentifier: The endpoint identifier. Does not neccessarily have to be the path of the endpoint.
        :param **dataConverters: The data converters. A dict with key as the data name and value as the converter function.
        :return:
        '''
        # Validate dataConverters
        for dataName in dataConverters:
            if not callable(dataConverters[dataName]):
                raise TypeError(
                    f"DataConverter for {dataName} is not callable.")

        # Validate endpointHandler
        if not callable(endpointHandler):
            raise TypeError("EndpointHandler is not callable.")

        # Validate endpointIdentifier
        if endpointIdentifier in self.endpointMap:
            raise ValueError("EndpointIdentifier is not unique.")

        # Analyse the endpointHandler
        varKeyword, nonOptionalParameters, optionalParameters = self.analyseParameters(
            endpointHandler)

        # Register endpoint
        self.endpointMap[endpointIdentifier] = {
            "endpointIdentifier": endpointIdentifier,
            "endpointHandler": endpointHandler,
            "dataConverters": dataConverters,
            "varKeyword": varKeyword,
            "nonOptionalParameters": nonOptionalParameters,
            "optionalParameters": optionalParameters,
            "metadata": metadata
        }

        # Notify installed protocols
        for protocolHandler in self.installedProtocols:
            protocolHandler.onNewEndpoint({
                "endpointIdentifier": endpointIdentifier,
                "endpointHandler": endpointHandler,
                "dataConverters": dataConverters,
                "varKeyword": varKeyword,
                "nonOptionalParameters": nonOptionalParameters,
                "optionalParameters": optionalParameters,
                "metadata": metadata
            })

    def endpoint(self, endpointIdentifier: str, metadata: dict = {}, **dataConverters: dict) -> None:
        def _endpoint_internal(func):
            self.register(
                endpointHandler=func, endpointIdentifier=endpointIdentifier, metadata=metadata, **dataConverters)

            @wraps(func)
            def __endpoint_internal(*args, **kwargs):
                return func(*args, **kwargs)
            return __endpoint_internal
        return _endpoint_internal

    def responseStandardizerProxy(self, realProtocolName):
        'Adds the protocolName to the standardizer call'
        def _responseStandardizerProxy(*args, protocolName=None, **kw):
            # protocolName here is used to prevent the user from modifying it.
            return self.installedResponseHandler.standardizeResponse(*args, protocolName=realProtocolName, **kw)
        return _responseStandardizerProxy

    def getDataProxy(self, getData, protocolName):
        def _getDataProxy(key):
            if key == "makeResponse":
                return self.responseStandardizerProxy(protocolName)
            return getData(key)
        return _getDataProxy

    def incomingRequest(self, protocol: StandardProtocolHandler, endpointIdentifier: str, getData: Callable, sendData: Callable):
        '''
        Handle an incoming request.
        :param endpointIdentifier: The endpoint identifier.
        :param getData: The getData function.
        :param sendData: The sendData function.
        :return:

        Notes on data priority:
        - HIGHEST: **kw when registering the endpoint
        - NORMAL: Incoming request data, from getData
        - LOWEST: Default data, from the endpoint handler
        '''
        # Replaces getData with proxy so it can handle "makeResponse"
        getData = self.getDataProxy(getData, protocol.name)

        # Validate endpointIdentifier
        if endpointIdentifier not in self.endpointMap:
            return sendData(self.installedResponseHandler.exceptionHandler(EndpointNotFound(endpointIdentifier), protocolName=protocol.name))

        # Get endpoint
        endpoint = self.endpointMap[endpointIdentifier]
        try:
            callDict = self.getCallDict(
                getData, varKeyword=endpoint["varKeyword"], nonOptionalParameters=endpoint["nonOptionalParameters"], optionalParameters=endpoint["optionalParameters"], dataConverters=endpoint["dataConverters"])
        except Exception as e:
            return sendData(self.installedResponseHandler.exceptionHandler(e, protocolName=protocol.name))

        # Validate the request
        for validator in self.installedValidators:
            evaluate = validator.getEvaluationMethod(endpoint)
            varKeyword, nonOptionalParameters, optionalParameters = self.analyseParameters(
                evaluate)
            try:
                evaluationCallDict = self.getCallDict(varKeyword=varKeyword, nonOptionalParameters=nonOptionalParameters,
                                                      optionalParameters=optionalParameters, getData=getData)
            except Exception as e:
                return sendData(self.installedResponseHandler.exceptionHandler(e, protocolName=protocol.name))

            try:
                evaluate(**evaluationCallDict)
            except Exception as e:
                return sendData(self.installedResponseHandler.exceptionHandler(e, protocolName=protocol.name))
        # Call endpoint
        # Note: This does NOT return the data from the handler.
        return sendData(endpoint["endpointHandler"](**callDict))

    def useProtocol(self, protocolHandlerInstance: StandardProtocolHandler):
        protocolHandlerInstance.install(self)
        self.installedProtocols.append(protocolHandlerInstance)

    def useResponseHandler(self, standardizerInstance: StandardResponseHandler):
        'Standardizes the response'
        if not isinstance(self.installedResponseHandler, NoResponseHandler):
            raise Exception(
                "You can only register one responseHandler.")
        if not isinstance(standardizerInstance, StandardResponseHandler):
            raise TypeError(
                "ResponseHandler must be an instance of StandardResponseHandler")
        self.installedResponseHandler = standardizerInstance

    def useValidator(self, validator: StandardValidator):
        '''
        Install a validator.
        :param validator: The validator to use.
        '''
        if not isinstance(validator, StandardValidator):
            raise TypeError(
                "Validator must be an instance of StandardValidator.")
        validator.install(self)
        self.installedValidators.append(validator)

    def wait(self):
        while True:
            time.sleep(10000000)
