import json

from websocket import create_connection

from core.dict_object import DictObject
from core.logger import Logger


class WebsocketRelayWorker:
    def __init__(self, inbound_queue, url):
        self.logger = Logger(__name__)
        self.inbound_queue = inbound_queue
        self.url = url
        self.ws = None

    def run(self):
        self.ws = create_connection(self.url)
        self.logger.info("Connected to Websocket Relay!")

        result = self.ws.recv()
        while result:
            self.inbound_queue.append(DictObject(json.loads(result)))
            result = self.ws.recv()

        self.ws.close()

    def send_message(self, message):
        if self.ws:
            self.ws.send(message)
