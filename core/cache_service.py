from core.decorators import instance
from core.logger import Logger
from pathlib import Path
import os


@instance()
class CacheService:
    CACHE_DIR = os.sep + os.path.join("data", "cache")

    def __init__(self):
        Path(os.getcwd() + self.CACHE_DIR).mkdir(parents=True, exist_ok=True)
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.character_service = registry.get_instance("character_service")

    def store(self, group, filename, contents):
        base_path = os.getcwd() + self.CACHE_DIR + os.sep + group
        Path(base_path).mkdir(exist_ok=True)

        with open(base_path + os.sep + filename, "w") as f:
            f.write(contents)

    def retrieve(self, group, filename):
        base_path = os.getcwd() + self.CACHE_DIR + os.sep + group

        with open(base_path + os.sep + filename, "r") as f:
            return f.read()
