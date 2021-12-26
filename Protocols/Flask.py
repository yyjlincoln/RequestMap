from .ProtocolBase import StandardProtocolHandler
from flask import Flask, request, jsonify
import time
import json
import threading
import logging


class HTTPViaFlask(StandardProtocolHandler):
    def __init__(self, app=None, **flaskConfig):
        '''
        The flask protocol.
        Configure each endpoint using the metadata field "httpmethods" and "httproute".
        Variable keyword arguments are passed to the flask app when it starts.
        '''
        super().__init__()
        self.app = app
        self.config = flaskConfig
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

    def start(self) -> bool:
        if 'ALLOW_DEV_SERVER' in self.config:
            if self.config['ALLOW_DEV_SERVER']:
                threading.Thread(target=self.app.run,
                                 kwargs=self.config).start()
                return True

        logging.warn('''Not starting HTTPViaFlask in development mode. If you intend to launch the development server, pass through ALLOW_DEV_SERVER=True. If you are using a production server such as gunicorn, please ignore this message.''')
        return False


class HTTPBatchRequestViaFlask(StandardProtocolHandler):
    def __init__(self, app=None, route='/batch', **flaskConfig):
        super().__init__()
        self.app = app
        if not app:
            self.app = Flask(__name__)
        self.route = route
        self.name = "HTTPBatchRequestViaFlask"
        self.config = flaskConfig

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
        # Don't need to do anything.
        pass

    def start(self):
        if 'ALLOW_DEV_SERVER' in self.config:
            if self.config['ALLOW_DEV_SERVER']:
                threading.Thread(target=self.app.run,
                                 kwargs=self.config).start()
                return True

        logging.warn('''Not starting HTTPBatchRequestViaFlask in development mode. If you intend to launch the development server, pass through ALLOW_DEV_SERVER=True. If you are using a production server such as gunicorn, please ignore this message.''')
        return False


class HTTPRequestByEndpointIdentifier(StandardProtocolHandler):
    def __init__(self, app=None, route='/science', **flaskConfig):
        super().__init__()
        self.app = app
        if not app:
            self.app = Flask(__name__)
        self.route = route
        self.name = "HTTPRequestByEndpointIdentifier"
        self.config = flaskConfig

    def initialise(self):
        self.app.add_url_rule(
            self.route,
            'HTTPRequestByEndpointIdentifier-Main',
            self.handleCall,
            methods=['GET', 'POST']
        )

    def flaskGetDataProxy(self):
        def runtimeProxy(key):
            # This is neccessary as request.values can only be accessed within an endpoint.
            return request.values.get(key)
        return runtimeProxy

    def sendDataProxy(self, data):
        return data

    def handleCall(self):
        '''Request Format

        @param endpointIdentifier = "<endpointIdentifier>"
        @param data = json.dumps({
            "<key>": "<value>"
        })
        '''
        # Get endpointIdentifier
        endpointIdentifier = self.flaskGetDataProxy()('endpointIdentifier')
        if not endpointIdentifier:
            return jsonify({
                'code': -1,
                'message': 'No endpointIdentifier is provided.'
            }), 400
        # Get data

        response = self.map.incomingRequest(
            self, endpointIdentifier, self.flaskGetDataProxy(), lambda data: data)
        return jsonify(response)

    def onNewEndpoint(self, endpoint):
        pass

    def start(self):
        if 'ALLOW_DEV_SERVER' in self.config:
            if self.config['ALLOW_DEV_SERVER']:
                threading.Thread(target=self.app.run,
                                 kwargs=self.config).start()
                return True

        logging.warn('''Not starting HTTPRequestByEndpointIdentifier in development mode. If you intend to launch the development server, pass through ALLOW_DEV_SERVER=True. If you are using a production server such as gunicorn, please ignore this message.''')
        return False
