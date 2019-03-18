from core.command_param_types import Const, Any, Options
from core.db import DB
from core.decorators import instance, command, setting
from core.dict_object import DictObject
from core.setting_types import DictionarySettingType
from core.text import Text
import time


@instance()
class TopicController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("motd", "topic")

    @setting(name="topic", value="", description="The bot topic")
    def topic(self):
        return DictionarySettingType()

    @command(command="topic", params=[], access_level="all",
             description="Show the current topic")
    def topic_show_command(self, request):
        topic = self.topic().get_value()
        if topic:
            time_string = self.util.time_to_readable(int(time.time()) - topic["created_at"])
            return "Topic: <highlight>%s<end> [set by <highlight>%s<end>][%s ago]" % (topic["topic_message"], topic["created_by"]["name"], time_string)
        else:
            return "There is no current topic."

    @command(command="topic", params=[Options(["clear", "unset"])], access_level="all",
             description="Clears the current topic")
    def topic_clear_command(self, request, _):
        self.topic().set_value("")

        return "The topic has been cleared."

    @command(command="topic", params=[Const("set", is_optional=True), Any("topic_message")], access_level="all",
             description="Set the current topic")
    def topic_set_command(self, request, _, topic_message):
        sender = DictObject({"name": request.sender.name, "char_id": request.sender.char_id})

        topic = {"topic_message": topic_message,
                 "created_by": sender,
                 "created_at": int(time.time())}

        self.topic().set_value(topic)

        return "The topic has been set."
