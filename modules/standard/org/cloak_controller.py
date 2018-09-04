from core.chat_blob import ChatBlob
from core.decorators import instance, command, event
import time

from core.public_channel_service import PublicChannelService


@instance()
class CloakController:
    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.character_service = registry.get_instance("character_service")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("city", "cloak")

    @command(command="cloak", params=[], access_level="all",
             description="Show the current status of the city cloak and the cloak history")
    def cloak_show_command(self, request):
        data = self.db.query("SELECT c.*, p.name FROM cloak_status c LEFT JOIN player p ON c.char_id = p.char_id ORDER BY created_at DESC LIMIT 20")

        if len(data) == 0:
            return "Unknown status on cloak."
        else:
            one_hour = 3600

            row = data[0]
            time_since_change = int(time.time()) - row.created_at
            time_string = self.util.time_to_readable(time_since_change)

            if row.action == "off":
                if time_since_change >= one_hour:
                    msg = "The cloaking device is <orange>disabled<end>. It is possible to enable it."
                else:
                    msg = "The cloaking device is <orange>disabled<end>. It is possible to enable it in %s." % time_string
            else:
                if time_since_change >= one_hour:
                    msg = "The cloaking device is <green>enabled<end>. It is possible to disable it."
                else:
                    msg = "The cloaking device is <green>enabled<end>. It is possible to disable it in %s." % time_string

            request.reply(msg)

            blob = ""
            for row in data:
                action = "<green>on<end>" if row.action == "on" else "<orange>off<end>"
                blob += "%s turned the device %s at %s.\n" % (row.name, action, self.util.format_datetime(row.created_at))

            return ChatBlob("Cloak History", blob)

    @event(event_type=PublicChannelService.ORG_CHANNEL_MESSAGE_EVENT, description="Record when the city cloak is turned off and on")
    def city_cloak_event(self, event_type, event_data):
        extended_message = event_data.extended_message
        if extended_message and extended_message.category_id == 1001 and extended_message.instance_id == 1:
            char_name = extended_message.params[0]
            char_id = self.character_service.resolve_char_to_id(char_name)
            action = extended_message.params[1]
            self.db.exec("INSERT INTO cloak_status (char_id, action, created_at) VALUES (?, ?, ?)", [char_id, action, int(time.time())])
