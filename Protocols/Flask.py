from .ProtocolBase import StandardProtocolHandler
from ..EndpointMap import MissingParameter, ParameterConversionFailure, EndpointNotFound
from flask import Flask, request, jsonify
import time
import json


class HTTPViaFlask(StandardProtocolHandler):
    def __init__(self, app=None):
        '''The flask protocol. Configure each endpoint using the metadata field "httpmethods" and "httproute".'''
        super().__init__()
        self.app = app
        if not app:
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


class HTTPBatchRequestViaFlask(StandardProtocolHandler):
    def __init__(self, app=None, route='/batch'):
        super().__init__()
        self.app = app
        if not app:
            self.app = Flask(__name__)
        self.route = route
        self.name = "HTTPBatchRequestViaFlask"

    def initialise(self):
        self.app.add_url_rule(
            self.route,
            'HTTPBatchRequestViaFlask-Main',
            self.handleBatch,
            methods=['GET', 'POST']
        )

    def flaskGetDataProxy(self):
        def runtimeProxy(key):
            # This is neccessary as request.values can only be accessed within an endpoint.
            return request.values.get(key)
        return runtimeProxy

    def sendDataProxy(self, data):
        return data

    def handleBatch(self):
        '''Format of a batch request:
        [{
            "endpointIdentifier": "<endpointIdentifier>",
            "data": {
                "<key>": "<value>"
            }
        }, {...}]
        '''
        # Get batch data.
        batch = self.flaskGetDataProxy()('batch')
        if not batch:
            return jsonify({
                'code': -1,
                'message': 'No batch data is provided.'
            }), 400
        try:
            batch = json.loads(batch)
            assert isinstance(batch, list)
        except Exception:
            return jsonify({
                'code': -1,
                'message': 'Invalid batch JSON was provided.'
            }), 400

        batchResponse = []
        for request in batch:
            # Check if all required fields are present
            if 'endpointIdentifier' not in request:
                batchResponse.append({
                    'code': -1,
                    'message': 'Missing parameter: endpointIdentifier.'
                })
                continue
            if 'data' not in request:
                batchResponse.append({
                    'code': -1,
                    'message': 'Missing parameter: data.'
                })
                continue
            if not isinstance(request['data'], dict):
                batchResponse.append({
                    'code': -1,
                    'message': 'Invalid request: data must be a dictionary.'
                })
                continue
            # Request endpoint
            response = self.map.incomingRequest(
                self, request['endpointIdentifier'], request['data'].get, lambda data: data)

            batchResponse.append({
                'endpointIdentifier': request['endpointIdentifier'],
                'response': response,
                'handledAt': time.time()
            })
        return jsonify(batchResponse)

    def onNewEndpoint(self, endpoint):
        pass
