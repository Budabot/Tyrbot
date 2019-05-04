from core.command_param_types import Const, Any, Options
from core.db import DB
from core.decorators import instance, command, setting, event
from core.dict_object import DictObject
from core.private_channel_service import PrivateChannelService
from core.setting_types import DictionarySettingType
from core.text import Text
import time


@instance()
class TopicController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.private_channel_service: PrivateChannelService = registry.get_instance("private_channel_service")

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
            return self.format_topic_message(topic)
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

    def format_topic_message(self, topic):
        time_string = self.util.time_to_readable(int(time.time()) - topic["created_at"])
        return "Topic: <highlight>%s<end> [set by <highlight>%s<end>][%s ago]" % (topic["topic_message"], topic["created_by"]["name"], time_string)

    @event(PrivateChannelService.JOINED_PRIVATE_CHANNEL_EVENT, "Show topic to characters joining the private channel")
    def show_topic(self, _, event_data):
        topic = self.topic().get_value()
        if topic:
            self.bot.send_private_message(event_data.char_id, self.format_topic_message(topic))

    @event(PrivateChannelService.LEFT_PRIVATE_CHANNEL_EVENT, "Clear topic when there are no characters in the private channel")
    def clear_topic(self, _, event_data):
        if self.topic().get_value() and len(self.private_channel_service.get_all_in_private_channel()) == 0:
            self.topic().set_value("")
