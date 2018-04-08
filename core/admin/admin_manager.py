from core.decorators import instance
import os


@instance()
class AdminManager:
    ADMIN = "admin"
    MODERATOR = "moderator"

    def __init__(self):
        pass

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.access_manager = registry.get_instance("access_manager")

    def start(self):
        self.access_manager.register_access_level(self.ADMIN, 20, self.check_admin)
        self.access_manager.register_access_level(self.MODERATOR, 30, self.check_mod)
        self.db.load_sql_file("admin.sql", os.path.dirname(__file__))

    def check_admin(self, char_id):
        access_level = self.get_access_level(char_id)
        return access_level == self.ADMIN

    def check_mod(self, char_id):
        access_level = self.get_access_level(char_id)
        return access_level == self.MOD

    def get_access_level(self, char_id):
        row = self.db.query_single("SELECT access_level FROM admin WHERE char_id = ?", [char_id])
        if row:
            return row.access_level
        else:
            return None

    def add(self, char_id, access_level):
        if access_level in [self.MODERATOR, self.ADMIN]:
            # remove any existing admin access level first
            self.remove(char_id)
            self.db.exec("INSERT INTO admin (char_id, access_level) VALUES (?, ?)", [char_id, access_level])
            return True
        else:
            return False

    def remove(self, char_id):
        return self.db.exec("DELETE FROM admin WHERE char_id = ?", [char_id]) > 0

    def get_all(self):
        return self.db.query("SELECT c.*, a.access_level FROM admin a "
                             "LEFT JOIN character c ON a.char_id = c.char_id "
                             "ORDER BY a.access_level ASC, c.name ASC")
