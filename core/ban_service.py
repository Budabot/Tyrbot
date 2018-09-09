from core.decorators import instance
import time

from core.dict_object import DictObject


@instance()
class BanService:
    BAN_ADDED_EVENT = "ban_added"
    BAN_REMOVED_EVENT = "ban_removed"

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.event_service = registry.get_instance("event_service")

    def pre_start(self):
        self.event_service.register_event_type(self.BAN_ADDED_EVENT)
        self.event_service.register_event_type(self.BAN_REMOVED_EVENT)

    def add_ban(self, char_id, sender_char_id, duration, reason):
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
        return self.db.query("SELECT b.*, p1.name AS name, p2.name AS sender_name FROM ban_list b "
                             "LEFT JOIN player p1 ON b.char_id = p1.char_id LEFT JOIN player p2 ON b.sender_char_id = p2.char_id "
                             "WHERE ended_early != 1 AND (finished_at > ? OR finished_at = -1)", [t])
