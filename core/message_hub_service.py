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

    def register_message_source(self, source):
        if source not in self.sources:
            self.sources.append(source)

    def subscribe_message_source(self, destination, callback, default_sources):
        if destination in self.hub:
            raise Exception("Relay destination '%s' already subscribed" % destination)

        # TODO check if there are existing source subscriptions
        for source in default_sources:
            if source not in self.sources:
                raise Exception("Could not subscribe destination '%s' to source '%s' because source does not exist" % (destination, source))

        self.hub[destination] = (DictObject({"name": destination,
                                             "callback": callback,
                                             "subscribed_source": default_sources}))

    def send_message(self, source, sender, message, formatted_message):
        ctx = DictObject({"source": source,
                          "sender": sender,
                          "message": message,
                          "formatted_message": formatted_message})

        for _, c in self.hub.items():
            if source in c.subscribed_source:
                try:
                    c.callback(ctx)
                except Exception as e:
                    self.logger.error("", e)
