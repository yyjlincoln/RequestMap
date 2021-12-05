from functools import wraps
import inspect
from typing import Callable


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


class ProtocolHandler:
    def __init__(self):
        self.map = None

    def install(self, map):
        self.map = map
        self.initialise()

    def initialise(self):
        'The initialise method is called after the map has been registered'
        pass

    def onNewEndpoint(self, endpoint):
        'The onNewEndpoint method is called when a new endpoint is added'
        pass


class Map():
    def __init__(self) -> None:
        self.endpointMap = {}
        self.installedProtocols = []

    def register(self, endpointHandler: str, endpointIdentifier: str, **dataConverters: dict) -> None:
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
        varKeyword = False
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
                varKeyword = True
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
            "optionalParameters": optionalParameters
        }

        # Notify installed protocols
        for protocolHandler in self.installedProtocols:
            protocolHandler.onNewEndpoint({
                "endpointIdentifier": endpointIdentifier,
                "endpointHandler": endpointHandler,
                "dataConverters": dataConverters,
                "varKeyword": varKeyword,
                "nonOptionalParameters": nonOptionalParameters,
                "optionalParameters": optionalParameters
            })

    def endpoint(self, endpointIdentifier: str, **dataConverters: dict) -> None:
        def _endpoint_internal(func):
            self.register(
                endpointHandler=func, endpointIdentifier=endpointIdentifier, **dataConverters)

            @wraps(func)
            def __endpoint_internal(*args, **kwargs):
                return func(*args, **kwargs)
            return __endpoint_internal
        return _endpoint_internal

    def incomingRequest(self, endpointIdentifier: str, getData: Callable, sendData: Callable):
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
        # Validate endpointIdentifier
        if endpointIdentifier not in self.endpointMap:
            raise EndpointNotFound(endpointIdentifier)

        # Get endpoint
        endpoint = self.endpointMap[endpointIdentifier]
        callDict = {}

        # Check if all required parameters are present
        for parameter in endpoint["nonOptionalParameters"]:
            data = getData(parameter)
            if data == None:
                raise MissingParameter(parameter)
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
                    raise ParameterConversionFailure(parameter)

        # Call endpoint
        # Note: This does NOT return the data from the handler.
        return sendData(endpoint["endpointHandler"](**callDict))

    def useProtocol(self, protocolHandlerInstance: ProtocolHandler):
        protocolHandlerInstance.install(self)
