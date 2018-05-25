from core.decorators import instance
from core.db import DB
from core.text import Text


@instance()
class PlayfieldController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")

    def start(self):
        pass
