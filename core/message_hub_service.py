from core.decorators import instance
from core.dict_object import DictObject
from core.logger import Logger
from core.lookup.character_service import CharacterService
from core.text import Text


@instance()
class MessageHubService:
    def __init__(self):
        self.logger = Logger(__name__)
        self.hub = {}
        self.sources = []

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.setting_service = registry.get_instance("setting_service")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.text: Text = registry.get_instance("text")
        self.db = registry.get_instance("db")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS message_hub_subscriptions ( "
                     "destination VARCHAR(50) NOT NULL,"
                     "source VARCHAR(50) NOT NULL"
                     ")")

    def register_message_source(self, source):
        """Call during pre_start"""
        if source not in self.sources:
            self.sources.append(source)

    def register_message_destination(self, destination, callback, default_sources, invalid_sources=[]):
        """Call during start"""
        if destination in self.hub:
            raise Exception("Message hub destination '%s' already subscribed" % destination)

        for source in default_sources:
            if source not in self.sources:
                self.logger.warning("Could not subscribe destination '%s' to source '%s' because source does not exist" % (destination, source))
                # raise Exception("Could not subscribe destination '%s' to source '%s' because source does not exist" % (destination, source))

        self.hub[destination] = (DictObject({"name": destination,
                                             "callback": callback,
                                             "sources": default_sources,
                                             "invalid_sources": invalid_sources}))

        self.reload_mapping(destination)

    def reload_mapping(self, destination):
        data = self.db.query("SELECT source FROM message_hub_subscriptions WHERE destination = ?", [destination])
        if data:
            self.hub[destination].sources =  list(map(lambda x: x.source, data))

    def send_message(self, source, sender, message, formatted_message):
        ctx = DictObject({"source": source,
                          "sender": sender,
                          "message": message,
                          "formatted_message": formatted_message})

        for _, c in self.hub.items():
            if source in c.sources:
                try:
                    c.callback(ctx)
                except Exception as e:
                    self.logger.error("", e)

    def subscribe_to_source(self, destination, source):
        if source not in self.sources:
            raise Exception("Message hub source '%s' doeselecs not exist" % source)

        obj = self.hub.get(destination, None)
        if not obj:
            raise Exception("Message hub destination '%s' does not exist" % destination)

        if source not in obj.sources:
            self.db.exec("DELETE FROM message_hub_subscriptions WHERE destination = ?", [destination])

            obj.sources.append(source)
            for source in obj.sources:
                self.db.exec("INSERT INTO message_hub_subscriptions (destination, source)"
                             "VALUES (?, ?)", [destination, source])

    def unsubscribe_from_source(self, destination, source):
        #if source not in self.sources:
        #    raise Exception("Message hub source '%s' does not exist" % source)

        obj = self.hub.get(destination, None)
        if not obj:
            raise Exception("Message hub destination '%s' does not exist" % destination)

        if source in obj.sources:
            self.db.exec("DELETE FROM message_hub_subscriptions WHERE destination = ?", [destination])

            obj.sources.remove(source)
            for source in obj.sources:
                self.db.exec("INSERT INTO message_hub_subscriptions (destination, source)"
                             "VALUES (?, ?)", [destination, source])
