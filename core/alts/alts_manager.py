from core.decorators import instance


@instance()
class AltsManager:
    UNVALIDATED = 0
    VALIDATED = 1
    MAIN = 2

    def __init__(self):
        pass

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.character_manager = registry.get_instance("character_manager")
        self.pork_manager = registry.get_instance("pork_manager")

    def start(self):
        pass

    def get_alts(self, char_id, status=None):
        if not status:
            status = self.VALIDATED

        sql = "SELECT p.*, a.group_id, a.status FROM player p " \
              "LEFT JOIN alts a ON p.char_id = a.char_id " \
              "WHERE p.char_id = ? OR a.group_id = (" \
              "SELECT group_id FROM alts WHERE status >= ? AND char_id = ?) " \
              "ORDER BY a.status DESC, a.status DESC, p.level DESC"

        return self.db.query(sql, [char_id, status, char_id])

    def add_alt(self, sender_char_id, alt_char_id):
        alt_row = self.get_alt_status(alt_char_id)
        if alt_row:
            return False

        sender_row = self.get_alt_status(sender_char_id)
        if sender_row:
            if sender_row.status == self.MAIN or sender_row.status == self.VALIDATED:
                params = [alt_char_id, sender_row.group_id, self.VALIDATED]
            else:
                params = [alt_char_id, sender_row.group_id, self.UNVALIDATED]
        else:
            # main does not exist, create entry for it
            # TODO race condition here if something else is adding alts at the same time
            group_id = self.get_next_group_id()
            self.db.exec("INSERT INTO alts (char_id, group_id, status) VALUES (?, ?, ?)",
                         [sender_char_id, group_id, self.MAIN])

            # make sure char info exists in character table
            self.pork_manager.load_character_info(sender_char_id)

            params = [alt_char_id, group_id, self.VALIDATED]

        # make sure char info exists in character table
        self.pork_manager.load_character_info(alt_char_id)
        self.db.exec("INSERT INTO alts (char_id, group_id, status) VALUES (?, ?, ?)", params)
        return True

    def remove_alt(self, sender_char_id, alt_char_id):
        alt_row = self.get_alt_status(alt_char_id)
        sender_row = self.get_alt_status(sender_char_id)

        # sender and alt do not belong to the same group id
        if not alt_row or not sender_row or alt_row.group_id != sender_row.group_id:
            return False

        # cannot remove alt from an unvalidated sender
        if sender_row.status == self.UNVALIDATED:
            return False

        self.db.exec("DELETE FROM alts WHERE char_id = ?", [alt_char_id])
        return True

    def get_alt_status(self, char_id):
        return self.db.query_single("SELECT group_id, status FROM alts WHERE char_id = ?", [char_id])

    def get_next_group_id(self):
        row = self.db.query_single("SELECT (IFNULL(MAX(group_id), 0) + 1) AS next_group_id FROM alts")
        return row.next_group_id
