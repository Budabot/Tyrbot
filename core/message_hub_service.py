from core.decorators import instance
from core.dict_object import DictObject
from core.logger import Logger
from core.lookup.character_service import CharacterService
from core.text import Text


@instance()
class MessageHubService:
    DEFAULT_GROUP = "default"

    def __init__(self):
        self.logger = Logger(__name__)
        self.hub = {}

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.setting_service = registry.get_instance("setting_service")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.text: Text = registry.get_instance("text")

    def register_message_source(self, source, callback):
        if source in self.hub:
            raise Exception("Relay source '%s' already registered" % source)

        self.hub[source] = (DictObject({"source": source,
                                        "callback": callback,
                                        "group": self.DEFAULT_GROUP}))

    def send_message(self, source, sender, message, formatted_message):
        obj = self.hub.get(source, None)
        if not obj:
            return

        group = obj.group
        if not group:
            return

        ctx = DictObject({"source": source,
                          "sender": sender,
                          "message": message,
                          "formatted_message": formatted_message})

        for _, c in self.hub.items():
            if c.source != source and c.group == group:
                try:
                    c.callback(ctx)
                except Exception as e:
                    self.logger.error("", e)
