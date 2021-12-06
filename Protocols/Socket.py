from .ProtocolBase import StandardProtocolHandler
import socket
import struct
import threading
import logging
import json

class Socket(StandardProtocolHandler):
    def __init__(self, bind, port):
        ''''''
        super().__init__()
        self.name = "Socket"
        self.bind = bind
        self.port = port

    def initialise(self):
        self.startServer()

    def onNewEndpoint(self, endpoint):
        # We don't need to do anything here.
        pass

    def serverLoop(self):
        while True:
            try:
                client, address = self.server.accept()
                threading.Thread(target=self.clientLoop, args=(client, address)).start()
            except Exception as e:
                logging.error("Could not accept client: " + str(e))


    def clientLoop(self, client, address):
        buffer = b''
        while True:
            try:
                data = client.recv(1024)
                if data:
                    buffer += data
                    buffer = self.processBuffer(buffer, client)
                else:
                    client.close()
                    break
            except Exception as e:
                logging.error("Could not receive data from client: " + str(e))
                client.close()
                break
    
    def processBuffer(self, buffer, client):
        '''
        Data structure:
        - HEAD: 3s (3 bytes) - always 'PKG'
        - TYPE: 3s (3 bytes) - 'REQ' (request), 'RES' (response), 'ERR' (error)
        - IDENTIFIER: 10s (10 bytes) - random, unique identifier for the request
        - LENGTH: I (4 bytes) - length of the data
        - DATA: (LENGTH)s (LENGTH bytes) - data, in JSON form
        '''
        if len(buffer) >=20:
            # Check whether the packet is complete
            head = buffer[:20]
            body = buffer[20:]
            # Unpack the head
            try:
                head, requestType, identifier, dataLength = struct.unpack("!3s3s10sI", head)
            except:
                logging.error("Could not unpack head")
                client.close()
                return b''
            
            if len(body) < dataLength:
                # Not enough data, wait for more
                return buffer
            updatedBuffer = body[dataLength:]
            data = body[:dataLength]

            # Try and load the data using JSON
            try:
                data = json.loads(data)
            except:
                logging.error("Could not load data")
                # Send failure message
                data = b'{"error": "Could not load data"}'
                client.send(struct.pack('3s3s10sI', b'PKG', b'ERR', identifier, len(data)) + data)
                return updatedBuffer
            
            # TODO: Parse data, handle using map

            

    def startServer(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.bind, self.port))
        self.server.listen(5)
        threading.Thread(target=self.serverLoop).start()


    def temp(self):
        return self.map.incomingRequest(self, endpointIdentifier, self.flaskGetDataProxy(), self.sendDataProxy)

class SocketHelper():
    def __init__(self, socket, address):
        self.socket = socket
        self.address = address
        self.data = b''
        self.dataLock = threading.Lock()
        self.dataReady = threading.Event()
        self.dataReady.clear()
        self.dataReady.set()
        self.thread = threading.Thread(target=self.receiveData)
        self.thread.start()

    def receiveData(self):
        while True:
            try:
                data = self.socket.recv(1024)
                if data:
                    self.dataLock.acquire()
                    self.data += data
                    self.dataReady.set()
                    self.dataLock.release()
                else:
                    break
            except:
                break

    def getData(self, length):
        self.dataReady.wait()
        self.dataReady.clear()
        self.dataLock.acquire()
        data = self.data[:length]
        self.data = self.data[length:]
        self.dataLock.release()
        return data

    def sendData(self, data):
        self.socket.send(data)

    def close(self):
        self.socket.close()