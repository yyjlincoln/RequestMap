from .ProtocolBase import StandardProtocolHandler
from ..EndpointMap import MissingParameter, ParameterConversionFailure, EndpointNotFound
from flask import Flask, request, jsonify
import json


class HTTPViaFlask(StandardProtocolHandler):
    def __init__(self):
        '''The flask protocol. Configure each endpoint using the metadata field "httpmethods" and "httproute".'''
        super().__init__()
        self.app = Flask(__name__)
        self.name = "HTTPViaFlask"

    def initialise(self):
        for endpointIdentifier, endpoint in self.map.endpointMap.items():
            self.onNewEndpoint(endpoint)

    def flaskGetDataProxy(self):
        def runtimeProxy(key):
            # This is neccessary as request.values can only be accessed within an endpoint.
            return request.values.get(key)
        return runtimeProxy

    def sendDataProxy(self, data):
        return data

    def flaskProxy(self, endpointIdentifier):
        def proxyInternal():
            return self.map.incomingRequest(self, endpointIdentifier, self.flaskGetDataProxy(), self.sendDataProxy)
        return proxyInternal

    def onNewEndpoint(self, endpoint):
        if 'httpmethods' in endpoint['metadata']:
            methods = endpoint['metadata']['httpmethods']
        else:
            methods = ['GET', 'POST']

        if 'httproute' in endpoint['metadata']:
            route = endpoint['metadata']['httproute']
        else:
            route = '/' + endpoint['identifier']

        self.app.add_url_rule(
            route,
            endpoint['endpointIdentifier'],
            self.flaskProxy(endpoint['endpointIdentifier']),
            methods=methods
        )