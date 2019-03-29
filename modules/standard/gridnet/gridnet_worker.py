import json

from websocket import create_connection

from core.dict_object import DictObject
from core.logger import Logger


class GridnetWorker:
    def __init__(self, queue):
        self.logger = Logger(__name__)
        self.queue = queue

    def run(self):
        ws = create_connection("wss://gridnet.jkbff.com/subscribe/gridnet")
        self.logger.info("Connected to Gridnet!")

        result = ws.recv()
        while result:
            self.queue.append(DictObject(json.loads(result)))
            result = ws.recv()

        ws.close()
