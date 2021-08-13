from core.decorators import instance
from core.dict_object import DictObject
from core.logger import Logger
from pathlib import Path
import os


@instance()
class CacheService:
    CACHE_DIR = os.sep + os.path.join("data", "cache")

    def __init__(self):
        Path(os.getcwd() + self.CACHE_DIR).mkdir(parents=True, exist_ok=True)
        self.logger = Logger(__name__)

    def store(self, group, filename, contents):
        base_path, full_path = self.get_full_path(group, filename)
        Path(base_path).mkdir(exist_ok=True)

        with open(full_path, mode="w", encoding="UTF-8") as f:
            f.write(contents)

    def retrieve(self, group, filename):
        base_path, full_path = self.get_full_path(group, filename)

        try:
            with open(full_path, mode="r", encoding="UTF-8") as f:
                last_modified = int(os.path.getmtime(full_path))
                return DictObject({"data": f.read(), "last_modified": last_modified})
        except FileNotFoundError:
            return None

    def get_full_path(self, group, filename):
        base_path = os.getcwd() + self.CACHE_DIR + os.sep + group
        full_path = base_path + os.sep + filename
        return base_path, full_path
