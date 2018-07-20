from core.decorators import instance
from core.logger import Logger
import time


@instance()
class UsageManager:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.db = registry.get_instance("db")

    def add_usage(self, command, handler, char_id, channel):
        self.db.exec("INSERT INTO command_usage (command, handler, char_id, channel, created_at) VALUES (?, ?, ?, ?, ?)", [command, handler, char_id, channel, int(time.time())])
