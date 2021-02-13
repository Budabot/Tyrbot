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
        self.setting_service = registry.get_instance("setting_service")

    def start(self):
        self.command_alias_service.add_alias("motd", "topic")
        self.command_alias_service.add_alias("orders", "topic")

        self.setting_service.register(self.module_name, "topic", "", DictionarySettingType(), "The bot topic")

    @command(command="topic", params=[], access_level="all",
             description="Show the current topic")
    def topic_show_command(self, request):
        topic = self.get_topic()
        if topic:
            return self.format_topic_message(topic)
        else:
            return "There is no current topic."

    @command(command="topic", params=[Options(["clear", "unset"])], access_level="all",
             description="Clears the current topic")
    def topic_clear_command(self, request, _):
        self.clear_topic()

        return "The topic has been cleared."

    @command(command="topic", params=[Const("set", is_optional=True), Any("topic_message")], access_level="all",
             description="Set the current topic")
    def topic_set_command(self, request, _, topic_message):
        self.set_topic(topic_message, request.sender)

        return "The topic has been set."

    def format_topic_message(self, topic):
        time_string = self.util.time_to_readable(int(time.time()) - topic["created_at"])
        return "Topic: <highlight>%s</highlight> [set by <highlight>%s</highlight>][%s ago]" % (topic["topic_message"], topic["created_by"]["name"], time_string)

    def get_topic(self):
        return self.setting_service.get("topic").get_value()

    def clear_topic(self):
        self.setting_service.get("topic").set_value("")

    def set_topic(self, message, sender):
        topic = {"topic_message": message,
                 "created_by": {"char_id": sender.char_id, "name": sender.name},
                 "created_at": int(time.time())}

        self.setting_service.get("topic").set_value(topic)

    @event(PrivateChannelService.JOINED_PRIVATE_CHANNEL_EVENT, "Show topic to characters joining the private channel")
    def char_join_event(self, _, event_data):
        topic = self.get_topic()
        if topic:
            # TODO add conn
            self.bot.send_private_message(event_data.char_id, self.format_topic_message(topic))

    @event(PrivateChannelService.LEFT_PRIVATE_CHANNEL_EVENT, "Clear topic when there are no characters in the private channel")
    def char_leave_event(self, _, event_data):
        if self.get_topic() and len(self.private_channel_service.get_all_in_private_channel()) == 0:
            self.clear_topic()
