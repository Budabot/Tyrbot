from core.decorators import instance
import time

from core.dict_object import DictObject
from core.logger import Logger


@instance()
class BanService:
    BAN_ADDED_EVENT = "ban_added"
    BAN_REMOVED_EVENT = "ban_removed"

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.event_service = registry.get_instance("event_service")
        self.command_service = registry.get_instance("command_service")

    def pre_start(self):
        self.event_service.register_event_type(self.BAN_ADDED_EVENT)
        self.event_service.register_event_type(self.BAN_REMOVED_EVENT)
        self.command_service.register_command_pre_processor(self.check_for_banned)

    def add_ban(self, char_id, sender_char_id, duration=None, reason=None):
        reason = reason or ""

        t = int(time.time())
        if duration:
            finished_at = t + duration
        else:
            finished_at = -1

        num_rows = self.db.exec("INSERT INTO ban_list (char_id, sender_char_id, created_at, finished_at, reason, ended_early) VALUES (?, ?, ?, ?, ?, 0)",
                                [char_id, sender_char_id, t, finished_at, reason])

        if num_rows:
            self.event_service.fire_event(self.BAN_ADDED_EVENT, DictObject({"char_id": char_id, "sender_char_id": sender_char_id, "duration": duration, "reason": reason}))

        return num_rows

    def remove_ban(self, char_id):
        t = int(time.time())
        num_rows = self.db.exec("UPDATE ban_list SET ended_early = 1 WHERE char_id = ? AND (finished_at > ? OR finished_at = -1)", [char_id, t])

        if num_rows:
            self.event_service.fire_event(self.BAN_REMOVED_EVENT, DictObject({"char_id": char_id}))

        return num_rows

    def get_ban(self, char_id):
        t = int(time.time())
        return self.db.query_single("SELECT * FROM ban_list WHERE char_id = ? AND ended_early != 1 AND (finished_at > ? OR finished_at = -1)", [char_id, t])

    def get_ban_list(self):
        t = int(time.time())
        return self.db.query("SELECT b.*, COALESCE(p1.name, b.char_id) AS name, p2.name AS sender_name FROM ban_list b "
                             "LEFT JOIN player p1 ON b.char_id = p1.char_id LEFT JOIN player p2 ON b.sender_char_id = p2.char_id "
                             "WHERE ended_early != 1 AND (finished_at > ? OR finished_at = -1) "
                             "ORDER BY b.created_at DESC", [t])

    def check_for_banned(self, context):
        char_id = context.char_id
        if self.get_ban(char_id):
            # do nothing if character is banned
            self.logger.info("ignoring banned character %d for command '%s'" % (char_id, context.message))
            return False
        else:
            return True
