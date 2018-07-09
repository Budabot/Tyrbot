from core.command_param_types import Const, Any
from core.db import DB
from core.decorators import instance, command, setting
from core.setting_types import DictionarySettingType
from core.text import Text
import time


@instance()
class TopicController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.access_manager = registry.get_instance("access_manager")
        self.character_manager = registry.get_instance("character_manager")

    @setting(name="topic", value="", description="The bot topic")
    def topic(self):
        return DictionarySettingType()

    @command(command="topic", params=[], access_level="all",
             description="Show the current topic")
    def topic_show_command(self, channel, sender, reply, args):
        topic = self.topic().get_value()
        if topic:
            time_string = self.util.time_to_readable(int(time.time()) - topic["created_at"])
            reply("Topic: <highlight>%s<end> [set by <highlight>%s<end>][%s ago]" % (topic["topic_message"], topic["created_by"]["name"], time_string))
        else:
            reply("There is no current topic.")

    @command(command="topic", params=[Const("clear")], access_level="all",
             description="Clears the current topic")
    def topic_clear_command(self, channel, sender, reply, args):
        self.topic().set_value("")

        reply("The topic has been cleared.")

    @command(command="topic", params=[Const("set", is_optional=True), Any("topic_message")], access_level="all",
             description="Set the current topic")
    def topic_set_command(self, channel, sender, reply, args):
        topic_message = args[1]

        topic = {"topic_message": topic_message,
                 "created_by": sender.row,
                 "created_at": int(time.time())}

        self.topic().set_value(topic)

        reply("The topic has been set.")
