import time

from core.aochat.server_packets import PublicChannelMessage
from core.chat_blob import ChatBlob
from core.conn import Conn
from core.decorators import instance, command, event, timerevent
from core.dict_object import DictObject
from core.sender_obj import SenderObj


@instance()
class CloakController:
    MESSAGE_SOURCE = "cloak_reminder"
    CLOAK_EVENT = "cloak"

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.character_service = registry.get_instance("character_service")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.timer_controller = registry.get_instance("timer_controller", is_optional=True)
        self.event_service = registry.get_instance("event_service")
        self.access_service = registry.get_instance("access_service")
        self.message_hub_service = registry.get_instance("message_hub_service")

    def pre_start(self):
        self.bot.register_packet_handler(PublicChannelMessage.id, self.handle_public_message)
        self.event_service.register_event_type(self.CLOAK_EVENT)
        self.message_hub_service.register_message_source(self.MESSAGE_SOURCE)

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS cloak_status (char_id INT NOT NULL, action VARCHAR(10) NOT NULL, created_at INT NOT NULL)")
        self.command_alias_service.add_alias("city", "cloak")

    @command(command="cloak", params=[], access_level="org_member",
             description="Show the current status of the city cloak and the cloak history")
    def cloak_show_command(self, request):
        data = self.db.query("SELECT c.*, p.name FROM cloak_status c LEFT JOIN player p ON c.char_id = p.char_id ORDER BY created_at DESC LIMIT 20")

        if len(data) == 0:
            return "Unknown status on cloak."
        else:
            msg = self.get_cloak_status(data[0])

            request.reply(msg)

            blob = ""
            for row in data:
                action = "<green>on</green>" if row.action == "on" else "<orange>off</orange>"
                blob += "%s turned the device %s at %s.\n" % (row.name, action, self.util.format_datetime(row.created_at))

            return ChatBlob("Cloak History", blob)

    @event(event_type=CLOAK_EVENT, description="Record when the city cloak is turned off and on", is_hidden=True)
    def city_cloak_event(self, event_type, event_data):
        self.db.exec("INSERT INTO cloak_status (char_id, action, created_at) VALUES (?, ?, ?)", [event_data.sender.char_id, event_data.action, int(time.time())])

    @timerevent(budatime="15m", description="Reminds the players to toggle the cloak")
    def cloak_reminder_event(self, event_type, event_data):
        data = self.db.query("SELECT c.*, p.name FROM cloak_status c LEFT JOIN player p ON c.char_id = p.char_id ORDER BY created_at DESC LIMIT 1")

        for row in data:
            one_hour = 3600
            t = int(time.time())
            time_until_change = row.created_at + one_hour - t
            if row.action == "off":
                if time_until_change <= 0:
                    time_str = self.util.time_to_readable(t - row.created_at)
                    msg = "The cloaking device is <orange>disabled</orange> but can be enabled. <highlight>%s</highlight> disabled it %s ago." % (row.name, time_str)
                    self.message_hub_service.send_message(self.MESSAGE_SOURCE, None, None, msg)

    @event(event_type=CLOAK_EVENT, description="Set a timer for when cloak can be raised and lowered")
    def city_cloak_timer_event(self, event_type, event_data):
        if event_data.action == "off":
            timer_name = "Raise City Cloak"
        elif event_data.action == "on":
            timer_name = "Lower City Cloak"
        else:
            raise Exception("Unknown cloak action '%s'" % event_data.action)

        self.timer_controller.add_timer(timer_name, event_data.sender.char_id, "org", int(time.time()), 3600)

    def get_cloak_status(self, row):
        one_hour = 3600
        time_until_change = row.created_at + one_hour - int(time.time())
        time_string = self.util.time_to_readable(time_until_change)

        if row.action == "off":
            if time_until_change <= 0:
                msg = "The cloaking device is <orange>disabled</orange>. It is possible to enable it."
            else:
                msg = "The cloaking device is <orange>disabled</orange>. It is possible to enable it in %s." % time_string
        else:
            if time_until_change <= 0:
                msg = "The cloaking device is <green>enabled</green>. It is possible to disable it."
            else:
                msg = "The cloaking device is <green>enabled</green>. It is possible to disable it in %s." % time_string

        return msg

    def handle_public_message(self, conn: Conn, packet: PublicChannelMessage):
        if not conn.is_main:
            return

        extended_message = packet.extended_message
        if extended_message and extended_message.category_id == 1001 and extended_message.instance_id == 1:
            char_name = extended_message.params[0]
            char_id = self.character_service.resolve_char_to_id(char_name)
            action = extended_message.params[1]
            access_level = self.access_service.get_access_level(char_id)
            self.event_service.fire_event(self.CLOAK_EVENT, DictObject({"sender": SenderObj(char_id, char_name, access_level), "action": action}))
