from core.cache_service import CacheService
from core.decorators import instance
from core.dict_object import DictObject
from core.logger import Logger
import requests
import json

from core.tyrbot import Tyrbot


@instance()
class CharacterHistoryService:
    CACHE_GROUP = "history"
    CACHE_MAX_AGE = 86400

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.cache_service: CacheService = registry.get_instance("cache_service")

    def get_character_history(self, name, server_num):
        cache_key = "%s.%d.json" % (name, server_num)

        # check cache for fresh value
        cache_result = self.cache_service.retrieve(self.CACHE_GROUP, cache_key, self.CACHE_MAX_AGE)
        if cache_result:
            result = json.loads(cache_result)
        else:
            url = "http://pork.budabot.jkbff.com/pork/history.php?server=%d&name=%s" % (server_num, name)

            r = requests.get(url)
            try:
                result = r.json()
            except ValueError as e:
                self.logger.warning("Error marshalling value as json: %s" % r.text, e)
                result = None

            if result:
                # store result in cache
                self.cache_service.store(self.CACHE_GROUP, cache_key, json.dumps(result))
            else:
                # check cache for any value, even expired
                result = self.cache_service.retrieve(self.CACHE_GROUP, cache_key)

        if result:
            return map(lambda x: DictObject(x), result)
        else:
            return None
