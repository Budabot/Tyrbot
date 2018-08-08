from core.db import DB
from core.decorators import instance
import time


@instance()
class BanService:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")

    def add_ban(self, char_id, sender_char_id, duration, reason):
        t = int(time.time())
        if duration:
            finished_at = t + duration
        else:
            finished_at = -1
        return self.db.exec("INSERT INTO ban_list (char_id, sender_char_id, created_at, finished_at, reason, ended_early) VALUES (?, ?, ?, ?, ?, 0)",
                            [char_id, sender_char_id, t, finished_at, reason])

    def remove_ban(self, char_id):
        t = int(time.time())
        return self.db.exec("UPDATE ban_list SET ended_early = 1 WHERE char_id = ? AND (finished_at > ? OR finished_at = -1)", [char_id, t])

    def get_ban(self, char_id):
        t = int(time.time())
        return self.db.query_single("SELECT * FROM ban_list WHERE char_id = ? AND ended_early != 1 AND (finished_at > ? OR finished_at = -1)", [char_id, t])

    def get_ban_list(self):
        t = int(time.time())
        return self.db.query("SELECT b.*, p1.name AS name, p2.name AS sender_name FROM ban_list b "
                             "LEFT JOIN player p1 ON b.char_id = p1.char_id LEFT JOIN player p2 ON b.sender_char_id = p2.char_id "
                             "WHERE ended_early != 1 AND (finished_at > ? OR finished_at = -1)", [t])
