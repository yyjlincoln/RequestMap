from functools import wraps
import inspect
from typing import Any, Callable

from .Response.ResponseBase import NoResponseHandler, StandardResponseHandler
from .Protocols.ProtocolBase import StandardProtocolHandler


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
        parameters = inspect.signature(endpointHandler).parameters
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
        callDict = {}

        # Check if all required parameters are present
        for parameter in endpoint["nonOptionalParameters"]:
            data = getData(parameter)
            if data == None:
                return sendData(self.installedResponseHandler.exceptionHandler(MissingParameter(parameter), protocolName=protocol.name))
            else:
                callDict[parameter] = data

        # Add optional parameters
        for parameter in endpoint["optionalParameters"]:
            data = getData(parameter)
            if data != None:
                callDict[parameter] = data

        # Convert Parameters
        for parameter in endpoint["dataConverters"]:
            if parameter in callDict:
                try:
                    callDict[parameter] = endpoint["dataConverters"][parameter](
                        callDict[parameter])
                except:
                    return sendData(self.installedResponseHandler.exceptionHandler(ParameterConversionFailure(parameter), protocolName=protocol.name))

        if endpoint["varKeyword"] != None:
            callDict[endpoint["varKeyword"]] = JITDict(getData)

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
