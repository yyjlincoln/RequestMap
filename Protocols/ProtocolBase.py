class StandardProtocolHandler:
    def __init__(self):
        self.map = None
        self.name = None

    def install(self, map) -> None:
        self.map = map
        self.initialise()
        if not self.name:
            raise Exception(
                "Can not install the ProtocolHandler. ProtocolHandler must have a name. Please define self.name in __init__")

    def initialise(self) -> None:
        'The initialise method is called after the map has been registered'
        pass

    def onNewEndpoint(self, endpoint: dict) -> None:
        'The onNewEndpoint method is called when a new endpoint is added'
        pass

    def start(self) -> bool:
        'The start method is called when the map is started'
        pass
