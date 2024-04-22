import time

from requests import ReadTimeout

from core.decorators import instance
from core.dict_object import DictObject
from core.logger import Logger
import requests
import json

from core.setting_types import TextSettingType


@instance()
class CharacterHistoryService:
    CACHE_GROUP = "history"
    CACHE_MAX_AGE = 86400

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.cache_service = registry.get_instance("cache_service")
        self.setting_service = registry.get_instance("setting_service")

    def start(self):
        self.setting_service.register("core.system", "pork_history_url", "https://pork.jkbff.com/pork/history.php?server={dimension}&name={name}",
                                      TextSettingType(["https://pork.jkbff.com/pork/history.php?server={dimension}&name={name}"]),
                                      "URL to lookup character history")

    def get_character_history(self, name, server_num):
        cache_key = "%s.%d.json" % (name, server_num)

        t = int(time.time())
        result = None

        # check cache for fresh value
        cache_result = self.cache_service.retrieve(self.CACHE_GROUP, cache_key)
        if cache_result and cache_result.last_modified > (t - self.CACHE_MAX_AGE):
            # TODO set cache age
            result = json.loads(cache_result.data)
        else:
            url = self.get_pork_url(server_num, name)

            try:
                r = requests.get(url, headers={"User-Agent": f"Tyrbot {self.bot.version}"}, timeout=5)
                if r.status_code == 200:
                    result = r.json()
                else:
                    self.logger.warning(f"Unexpected response received from '{url}': {r.status_code} '{r.text}'")
            except ReadTimeout:
                self.logger.warning("Timeout while requesting '%s'" % url)
                result = None
            except Exception as e:
                self.logger.error("Error requesting history for url '%s'" % url, e)
                result = None

            if result:
                # store result in cache
                self.cache_service.store(self.CACHE_GROUP, cache_key, json.dumps(result))
            elif cache_result:
                # check cache for any value, even expired
                result = json.loads(cache_result.data)

        if result:
            # TODO set cache age
            return map(lambda x: DictObject(x), result)
        else:
            return None

    def get_pork_url(self, dimension, char_name):
        return self.setting_service.get_value("pork_history_url").format(dimension=dimension, name=char_name)
