import json

from websocket import create_connection

from core.dict_object import DictObject
from core.logger import Logger


class GridnetWorker:
    def __init__(self, queue, url):
        self.logger = Logger(__name__)
        self.queue = queue
        self.url = url
        
        self.running = False
        self.ws = None

    def run(self):
        self.running = True
        self.ws = create_connection(self.url)
        self.logger.info("Connected to Gridnet!")

        result = self.ws.recv()

        while result and self.running:
            self.queue.append(DictObject(json.loads(result)))
            result = self.ws.recv()

        if self.ws.connected:
            self.ws.close()

        self.logger.info("Disconnected from Gridnet")

    def stop(self):
        self.running = False
        self.ws.close()
