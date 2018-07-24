from core.decorators import instance
from core.dict_object import DictObject
from core.logger import Logger
from __init__ import none_to_empty_string
import requests
import datetime


@instance()
class CharacterHistoryService:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.character_service = registry.get_instance("character_service")
        self.pork_service = registry.get_instance("pork_service")

    def get_character_history(self, name, server_num):
        url = "http://pork.budabot.jkbff.com/pork/history.php?server=%d&name=%s" % (server_num, name)

        r = requests.get(url)
        try:
            json = r.json()
        except ValueError as e:
            self.logger.warning("Error marshalling value as json: %s" % r.text, e)
            json = None

        return map(lambda x: DictObject(x), json)
