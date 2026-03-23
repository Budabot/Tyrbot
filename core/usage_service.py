from core.registry import Registry
from core.decorators import instance
from core.logger import Logger
import time


@instance()
class UsageService:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry: Registry):
        self.db = registry.get_instance("db")

    def add_usage(self, command: str, handler: str, char_id: int, channel: str):
        self.db.exec("INSERT INTO command_usage (command, handler, char_id, channel, created_at) VALUES (?, ?, ?, ?, ?)", [command, handler, char_id, channel, int(time.time())])
