import requests
from core.decorators import instance
from core.logger import Logger


@instance()
class OrgPorkManager:
    def __init__(self):
        self.logger = Logger("org_pork_manager")

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.character_manager = registry.get_instance("character_manager")

    def get_org_info(self, org_id):
        url = "http://people.anarchy-online.com/org/stats/d/%d/name/%d/basicstats.xml?data_type=json" % (self.bot.dimension, org_id)

        r = requests.get(url)
        try:
            json = r.json()
        except ValueError as e:
            self.logger.warning("Error marshalling value as json: %s" % r.text, e)
            json = None

        return json
