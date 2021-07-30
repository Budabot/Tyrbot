import json

from websocket import create_connection

from core.logger import Logger
from core.dict_object import DictObject


class WebsocketRelayWorker:
    def __init__(self, inbound_queue, url, user_agent):
        self.logger = Logger(__name__)
        self.inbound_queue = inbound_queue
        self.url = url
        self.ws = None
        self.user_agent = user_agent

    def run(self):
        self.ws = create_connection(self.url, header={"User-Agent": self.user_agent})
        self.logger.info("Connected to Websocket Relay!")
        self.inbound_queue.append(DictObject({"type": "connected"}))

        result = self.ws.recv()
        while result:
            obj = DictObject(json.loads(result))
            self.inbound_queue.append(obj)
            result = self.ws.recv()

        self.ws.close()

    def send_message(self, message):
        if self.ws:
            self.ws.send(message)

    def close(self):
        if self.ws:
            self.ws.close()
