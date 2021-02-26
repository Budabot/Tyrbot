import time

from core.buddy_service import BuddyService
from core.command_param_types import Const, Character, Options
from core.decorators import instance, command, event
from core.chat_blob import ChatBlob


@instance()
class TrackController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.buddy_service = registry.get_instance("buddy_service")
        self.util = registry.get_instance("util")
        self.text = registry.get_instance("text")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS track (char_id INT NOT NULL PRIMARY KEY, added_by_char_id INT NOT NULL, created_at INT NOT NULL)")
        self.db.exec("CREATE TABLE IF NOT EXISTS track_log (char_id INT NOT NULL, action VARCHAR(10) NOT NULL, created_at INT NOT NULL)")

    @command(command="track", params=[], access_level="member",
             description="Show the track list")
    def track_cmd(self, request):
        data = self.get_all_tracked_chars()
        blob = ""
        for row in data:
            blob += self.text.make_tellcmd(row.name, "track %s" % row.name) + " - " + ("<green>Online</green>" if self.buddy_service.is_online(row.char_id) == True else "<red>Offline</red>") + "\n"

        return ChatBlob("Track List", blob)

    @command(command="track", params=[Const("add"), Character("char")], access_level="member",
             description="Add a character to the track list")
    def track_add_cmd(self, request, _, char):
        if self.get_tracked_char(char.char_id):
            return "already tracked message"
        
        self.add_tracked_char(char.char_id, request.sender.char_id)
        return "%s is now being tracked." % char.name

    @command(command="track", params=[Options(["rem", "remove"]), Character("char")], access_level="member",
             description="Remove a character from the track list")
    def track_remove_cmd(self, request, _, char):
        if not self.get_tracked_char(char.char_id):
            return "%s is already being tracked." % char.name

        self.remove_tracked_char(char.char_id)
        return "%s has been removed from the track list." % char.name

    @command(command="track", params=[Const("view", is_optional=True), Character("char")], access_level="member",
             description="View tracking history for a char")
    def track_view_cmd(self, request, _, char):
        if not self.get_tracked_char(char.char_id):
            return "%s is not on the track list." % char.name
        
        data = self.get_track_log(char.char_id)
        blob = ""
        for row in data:
            datetime_str = self.util.format_datetime(row.created_at)
            blob += datetime_str + " - " + ("<green>Logon</green>" if row.action == "logon" else "<red>Logoff</red>") + "\n"
#            blob += "%s" % ("<green>Logon</green>" if row.action == "logon" else "<red>Logoff</red>") + " - " + datetime_str + "\n"    
        return ChatBlob("Track history for %s" % char.name, blob)

    @event(event_type=BuddyService.BUDDY_LOGON_EVENT, description="Record when a tracked char logs on", is_hidden=True)
    def buddy_logon_event(self, event_type, event_data):
            if self.get_tracked_char(event_data.char_id):
                self.add_track_info(event_data.char_id, "logon")

    @event(event_type=BuddyService.BUDDY_LOGOFF_EVENT, description="Record when a tracked char logs off", is_hidden=True)
    def buddy_logoff_event(self, event_type, event_data):
        if self.bot.is_ready():
            if self.get_tracked_char(event_data.char_id):
                self.add_track_info(event_data.char_id, "logoff")

    def get_tracked_char(self, char_id):
        return self.db.query_single("SELECT COALESCE(p1.name, t.char_id) AS name, COALESCE(p2.name, t.added_by_char_id) AS added_by_name, created_at "
                                    "FROM track t "
                                    "LEFT JOIN player p1 ON t.char_id = p1.char_id "
                                    "LEFT JOIN player p2 ON t.added_by_char_id = p2.char_id "
                                    "WHERE t.char_id = ?", [char_id])

    def get_all_tracked_chars(self):
        return self.db.query("SELECT COALESCE(p1.name, t.char_id) AS name, COALESCE(p2.name, t.added_by_char_id) AS added_by_name, created_at, t.char_id "
                                    "FROM track t "
                                    "LEFT JOIN player p1 ON t.char_id = p1.char_id "
                                    "LEFT JOIN player p2 ON t.added_by_char_id = p2.char_id ")

    def get_track_log(self, char_id):
        return self.db.query("SELECT action, created_at FROM track_log "
                             "WHERE char_id = ?", [char_id])

    def add_tracked_char(self, char_id, added_by_char_id):
        self.buddy_service.add_buddy(char_id, "track")
        self.db.exec("INSERT INTO track (char_id, added_by_char_id, created_at) VALUES (?, ?, ?)",
                     [char_id, added_by_char_id, int(time.time())])

    def remove_tracked_char(self, char_id):
        self.buddy_service.remove_buddy(char_id, "track")
        self.db.exec("DELETE FROM track WHERE char_id = ?", [char_id])

    def add_track_info(self, char_id, action):
        self.db.exec("INSERT INTO track_log (char_id, action, created_at) VALUES (?, ?, ?)",
                     [char_id, action, int(time.time())])
