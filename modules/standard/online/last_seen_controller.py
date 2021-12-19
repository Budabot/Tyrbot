import time

from core.buddy_service import BuddyService
from core.chat_blob import ChatBlob
from core.command_param_types import Character, NamedFlagParameters
from core.decorators import instance, command, event
from core.logger import Logger


@instance()
class LastSeenController:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.buddy_service = registry.get_instance("buddy_service")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS last_seen (char_id INT NOT NULL PRIMARY KEY, "
                     "dt INT NOT NULL DEFAULT 0)")

    @command(command="lastseen", params=[Character("character"), NamedFlagParameters(["show_all"])], access_level="org_member",
             description="Show the last time an org member was online (on any alt)")
    def lastseen_cmd(self, request, char, flag_params):
        sql = "SELECT p.*, a.group_id, a.status, l.dt FROM player p " \
              "LEFT JOIN alts a ON p.char_id = a.char_id " \
              "LEFT JOIN last_seen l ON p.char_id = l.char_id " \
              "WHERE p.char_id = ? OR a.group_id = (SELECT group_id FROM alts WHERE char_id = ?) " \
              "ORDER BY l.dt DESC, p.name ASC"

        data = self.db.query(sql, [char.char_id, char.char_id])
        blob = ""
        if len(data) == 0:
            return f"No lastseen information for <highlight>{char.name}</highlight> has been recorded."
        else:
            if flag_params.show_all:
                for row in data:
                    blob += f"<highlight>{row.name}</highlight>"
                    if row.dt:
                        blob += " last seen at " + self.util.format_datetime(row.dt)
                    else:
                        blob += " unknown"
                    blob += "\n\n"

                return ChatBlob("Last Seen Info for %s (%d)" % (char.name, len(data)), blob)
            else:
                online_alts = list(filter(lambda x: self.buddy_service.is_online(x.char_id), data))
                if online_alts:
                    online_alts_str = ", ".join(map(lambda x: f"<highlight>{x.name}</highlight>", online_alts))

                    return f"<highlight>{char.name}</highlight> is <green>online</green> with: {online_alts_str}."
                else:
                    alt_name = data[0].name
                    if data[0].dt:
                        last_seen = self.util.format_datetime(data[0].dt)
                        return f"<highlight>{char.name}</highlight> was last seen online with <highlight>{alt_name}</highlight> at <highlight>{last_seen}</highlight>."
                    else:
                        return f"No lastseen information for <highlight>{char.name}</highlight> has been recorded."

    @event(event_type=BuddyService.BUDDY_LOGON_EVENT, description="Record last seen info")
    def handle_buddy_logon_event(self, event_type, event_data):
        self.update_last_seen(event_data.char_id)

    def update_last_seen(self, char_id):
        t = int(time.time())
        if self.db.exec("UPDATE last_seen SET dt = ? WHERE char_id = ?", [t, char_id]) == 0:
            self.db.exec("INSERT IGNORE INTO last_seen (char_id, dt) VALUES (?, ?)", [char_id, t])

    def get_last_seen(self, char_id):
        return self.db.query_single("SELECT dt FROM last_seen WHERE char_id = ?", [char_id])
