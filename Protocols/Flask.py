from .ProtocolBase import StandardProtocolHandler
from ..EndpointMap import MissingParameter, ParameterConversionFailure, EndpointNotFound
from flask import Flask, request, jsonify
import json


class HTTPViaFlask(StandardProtocolHandler):
    def __init__(self):
        super().__init__()
        self.app = Flask(__name__)
        self.name = "HTTPViaFlask"

    def translateIdentifierToRoute(self, identifier):
        return "/" + identifier

    def translateRouteToIdentifier(self, route):
        return route[1:]

    def initialise(self):
        for endpointIdentifier, endpoint in self.map.endpointMap.items():
            self.onNewEndpoint(endpoint)

    def flaskGetDataProxy(self):
        def runtimeProxy(key):
            # This is neccessary as request.values can only be accessed within an endpoint.
            return request.values.get(key)
        return runtimeProxy

    def sendDataProxy(self):
        'Detects JSON and use jsonify if it is'
        def runtimeProxy(data):
            # Same thing. jsonify can only be accessed within an endpoint.
            try:
                json.loads(data)
                return jsonify(data)
            except:
                return data
        return runtimeProxy

    def flaskProxy(self, route):
        def proxyInternal():
            return self.map.incomingRequest(self.translateRouteToIdentifier(route), self.flaskGetDataProxy(), self.sendDataProxy())

        return proxyInternal

    def onNewEndpoint(self, endpoint):
        self.app.add_url_rule(
            self.translateIdentifierToRoute(endpoint['endpointIdentifier']),
            endpoint['endpointIdentifier'],
            self.flaskProxy(
                self.translateIdentifierToRoute(endpoint['endpointIdentifier'])),
            methods=['POST', 'GET']
        )
