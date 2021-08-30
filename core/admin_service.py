from core.decorators import instance


@instance()
class AdminService:
    ADMIN = "admin"
    MODERATOR = "moderator"

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.access_service = registry.get_instance("access_service")
        self.character_service = registry.get_instance("character_service")

    def pre_start(self):
        self.access_service.register_access_level(self.ADMIN, 20, self.check_admin)
        self.access_service.register_access_level(self.MODERATOR, 30, self.check_mod)

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS admin (char_id INT NOT NULL PRIMARY KEY, access_level VARCHAR(50) NOT NULL)")

    def check_admin(self, char_id):
        access_level = self.get_access_level(char_id)
        return access_level == self.ADMIN

    def check_mod(self, char_id):
        access_level = self.get_access_level(char_id)
        return access_level == self.MODERATOR

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
        superadmin_char_id = self.character_service.resolve_char_to_id(self.bot.superadmin)
        return self.db.query("SELECT p.*, t.char_id, t.access_level, t.sort FROM "
                             "(SELECT ? AS char_id, 'superadmin' AS access_level, 0 AS sort "
                             "UNION "
                             "SELECT a.char_id, a.access_level, "
                             "CASE WHEN access_level = 'admin' THEN 1 WHEN access_level = 'moderator' THEN 2 END AS sort FROM admin a) t "
                             "LEFT JOIN player p ON t.char_id = p.char_id "
                             "ORDER BY sort ASC, name ASC", [superadmin_char_id])
