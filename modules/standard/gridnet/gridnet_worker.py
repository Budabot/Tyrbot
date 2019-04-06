import json

from websocket import create_connection

from core.dict_object import DictObject
from core.logger import Logger


class GridnetWorker:
    def __init__(self, queue, url):
        self.logger = Logger(__name__)
        self.queue = queue
        self.url = url

    def run(self):
        ws = create_connection(self.url)
        self.logger.info("Connected to Gridnet!")

        result = ws.recv()
        while result:
            self.queue.append(DictObject(json.loads(result)))
            result = ws.recv()

        ws.close()
