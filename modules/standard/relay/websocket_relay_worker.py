import json

from websocket import create_connection, WebSocketConnectionClosedException

from core.logger import Logger
from core.dict_object import DictObject


class WebsocketRelayWorker:
    def __init__(self, inbound_queue, url, user_agent):
        self.logger = Logger(__name__)
        self.inbound_queue = inbound_queue
        self.url = url
        self.ws = None
        self.user_agent = user_agent
        self.is_running = True

    def run(self):
        self.ws = create_connection(self.url, header={"User-Agent": self.user_agent})
        self.logger.info("Connected to Websocket Relay!")
        self.inbound_queue.append(DictObject({"type": "connected"}))

        try:
            result = self.ws.recv()
            while result:
                obj = DictObject(json.loads(result))
                self.inbound_queue.append(obj)
                result = self.ws.recv()
        except WebSocketConnectionClosedException as e:
            if self.is_running:
                self.logger.error("", e)

        self.ws.close()

    def send_message(self, message):
        if self.ws:
            self.ws.send(message)

    def send_ping(self):
        try:
            if self.ws:
                self.ws.ping()
        except WebSocketConnectionClosedException as e:
            self.logger.error("", e)
            self.close()

    def close(self):
        if self.ws:
            self.is_running = False
            self.ws.close()
