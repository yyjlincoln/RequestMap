from functools import wraps
import inspect
from typing import Callable

from .Response.ResponseBase import NoResponseHandler, StandardResponseHandler
from .Protocols.ProtocolBase import StandardProtocolHandler
from .Validators.ValidatorBase import StandardValidator
from .Utilities.JITDictionary import JITDict
from .Exceptions import MissingParameter, ParameterConversionFailure, \
    EndpointNotFound, RequestMapException

import time
import logging


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
            if data is None:
                raise MissingParameter(parameter)
            else:
                callDict[parameter] = data

        # Add optional parameters
        for parameter in optionalParameters:
            data = getData(parameter)
            if data is not None:
                callDict[parameter] = data

        # Convert Parameters
        for parameter in dataConverters:
            if parameter in callDict:
                try:
                    callDict[parameter] = dataConverters[parameter](
                        callDict[parameter])
                except RequestMapException:
                    raise
                except Exception:
                    raise ParameterConversionFailure(parameter)

        if varKeyword is not None:
            callDict[varKeyword] = JITDict(getData)

        return callDict

    def register(self, endpointHandler: Callable, endpointIdentifier: str, metadata: dict = {}, **dataConverters: dict) -> None:
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

    def responseStandardizerProxy(self, realProtocol):
        'Adds the protocol to the standardizer call'
        def _responseStandardizerProxy(*args, protocol=None, **kw):
            # protocol here is used to prevent the user from modifying it.
            return self.installedResponseHandler.standardizeResponse(*args, protocol=realProtocol, **kw)
        return _responseStandardizerProxy

    def getDataProxy(self, getData, sendData, protocol, endpoint):
        def _getDataProxy(key):
            reservedDataNames = {
                'makeResponse': self.responseStandardizerProxy(protocol),
                'getData': self.getDataProxy(getData, sendData, protocol, endpoint),
                'protocol': protocol,
                'endpoint': endpoint,
                'sendData': sendData
            }
            if key in reservedDataNames:
                return reservedDataNames[key]
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

        # Validate endpointIdentifier
        if endpointIdentifier not in self.endpointMap:
            return sendData(self.installedResponseHandler.exceptionHandler(EndpointNotFound(endpointIdentifier), protocol=protocol))
        endpoint = self.endpointMap[endpointIdentifier]

        # Replaces getData with proxy so it can handle "makeResponse" and other reserved data names
        getData = self.getDataProxy(getData, sendData, protocol, endpoint)

        # Validate the request
        for validator in self.installedValidators:
            evaluate = validator.getEvaluationMethod(
                endpoint, protocol=protocol)
            if not callable(evaluate):
                raise TypeError(
                    "Evaluation method is not callable. Validator: " + str(validator) + ', endpointIdentifier: ' + str(endpoint['endpointIdentifier']) + ', protocolName: ' + str(protocol.name))
            varKeyword, nonOptionalParameters, optionalParameters = self.analyseParameters(
                evaluate)
            try:
                evaluationCallDict = self.getCallDict(varKeyword=varKeyword, nonOptionalParameters=nonOptionalParameters,
                                                      optionalParameters=optionalParameters, getData=getData)
            except Exception as e:
                return sendData(self.installedResponseHandler.exceptionHandler(e, protocol=protocol))

            try:
                evaluate(**evaluationCallDict)
            except Exception as e:
                return sendData(self.installedResponseHandler.exceptionHandler(e, protocol=protocol))

        # Prepare to call the endpoint
        try:
            callDict = self.getCallDict(
                getData, varKeyword=endpoint["varKeyword"], nonOptionalParameters=endpoint["nonOptionalParameters"], optionalParameters=endpoint["optionalParameters"], dataConverters=endpoint["dataConverters"])
        except Exception as e:
            return sendData(self.installedResponseHandler.exceptionHandler(e, protocol=protocol))

        # Calls the endpoint
        # Note: This does NOT return the data from the handler.
        try:
            return sendData(endpoint["endpointHandler"](**callDict))
        except Exception as e:
            return sendData(self.installedResponseHandler.exceptionHandler(e, protocol=protocol))

    def useProtocol(self, protocolHandlerInstance: StandardProtocolHandler):
        if not isinstance(protocolHandlerInstance, StandardProtocolHandler):
            raise TypeError(
                "protocolHandlerInstance must be an instance of StandardProtocolHandler.")
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

    def start(self):
        'Starts the server'
        for protocol in self.installedProtocols:
            if not protocol.start():
                logging.warn(f"Failed to start protocol: {protocol.name}")
