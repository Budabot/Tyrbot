import time

from core.buddy_service import BuddyService
from core.chat_blob import ChatBlob
from core.command_param_types import Character
from core.decorators import instance, command, event
from core.logger import Logger


@instance()
class LastSeenController:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.character_service = registry.get_instance("character_service")
        self.public_channel_service = registry.get_instance("public_channel_service")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS last_seen (char_id INT NOT NULL PRIMARY KEY, "
                     "dt INT NOT NULL DEFAULT 0)")

    @command(command="lastseen", params=[Character("character")], access_level="org_member",
             description="Show the last time an org member was online (on any alt)")
    def lastseen_cmd(self, request, char):
        sql = "SELECT p.*, a.group_id, a.status, l.dt FROM player p " \
              "LEFT JOIN alts a ON p.char_id = a.char_id " \
              "LEFT JOIN last_seen l ON p.char_id = l.char_id " \
              "WHERE p.char_id = ? OR a.group_id = (SELECT group_id FROM alts WHERE char_id = ?) " \
              "ORDER BY a.status DESC, p.level DESC, p.name ASC"

        data = self.db.query(sql, [char.char_id, char.char_id])
        blob = ""
        if len(data) == 0:
            blob += "Note: <highlight>%s</highlight> must be on the buddylist in order for <highlight>lastseen</highlight> data to be recorded." % char.name
        else:
            for row in data:
                blob += f"<highlight>{row.name}</highlight>"
                if row.dt:
                    blob += " last seen at " + self.util.format_datetime(row.dt)
                else:
                    blob += " unknown"
                blob += "\n\n"

        return ChatBlob("Last Seen for %s (%d)" % (char.name, len(data)), blob)

    @event(event_type=BuddyService.BUDDY_LOGON_EVENT, description="Record last seen info")
    def handle_org_member_logon_event(self, event_type, event_data):
        self.update_last_seen(event_data.char_id)

    def update_last_seen(self, char_id):
        t = int(time.time())
        if not self.db.exec("UPDATE last_seen SET dt = ? WHERE char_id = ?", [t, char_id]):
            self.db.exec("INSERT INTO last_seen (char_id, dt) VALUES (?, ?)", [char_id, t])
