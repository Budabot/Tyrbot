from core.decorators import instance


@instance()
class AltsService:
    CONFIRMED = 1
    MAIN = 2

    MAIN_CHANGED_EVENT_TYPE = "main_changed"

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.character_service = registry.get_instance("character_service")
        self.pork_service = registry.get_instance("pork_service")
        self.event_service = registry.get_instance("event_service")

    def pre_start(self):
        self.event_service.register_event_type(self.MAIN_CHANGED_EVENT_TYPE)

    def get_alts(self, char_id):
        sql = "SELECT p.*, a.group_id, a.status FROM player p " \
              "LEFT JOIN alts a ON p.char_id = a.char_id " \
              "WHERE p.char_id = ? OR a.group_id = (" \
              "SELECT group_id FROM alts WHERE char_id = ?) " \
              "ORDER BY a.status DESC, p.level DESC, p.name ASC"

        return self.db.query(sql, [char_id, char_id])

    def add_alt(self, sender_char_id, alt_char_id):
        alts = self.get_alts(alt_char_id)
        if len(alts) > 1:
            return ["another_main", False]

        sender_row = self.get_alt_status(sender_char_id)
        if sender_row:
            # if alt has no other alts, but still has a record in the alts table, delete record
            # so it can be assigned to another group_id
            if len(alts) == 1:
                self.event_service.fire_event(self.MAIN_CHANGED_EVENT_TYPE, {"old_main_id": alt_char_id, "new_main_id": self.get_main(sender_char_id)})
                self.db.exec("DELETE FROM alts WHERE char_id = ?", [alt_char_id])

            params = [alt_char_id, sender_row.group_id, self.CONFIRMED]
        else:
            group_id = self.get_next_group_id()

            # main does not exist, create entry for it
            self.db.exec("INSERT INTO alts (char_id, group_id, status) VALUES (?, ?, ?)",
                         [sender_char_id, group_id, self.MAIN])

            self.event_service.fire_event(self.MAIN_CHANGED_EVENT_TYPE, {"old_main_id": alt_char_id, "new_main_id": sender_char_id})

            # make sure char info exists in character table
            self.pork_service.load_character_info(sender_char_id)

            params = [alt_char_id, group_id, self.CONFIRMED]

        # make sure char info exists in character table
        self.pork_service.load_character_info(alt_char_id)
        self.db.exec("INSERT INTO alts (char_id, group_id, status) VALUES (?, ?, ?)", params)
        return ["success", True]

    def remove_alt(self, sender_char_id, alt_char_id):
        alt_row = self.get_alt_status(alt_char_id)
        sender_row = self.get_alt_status(sender_char_id)

        # sender and alt do not belong to the same group id
        if not alt_row or not sender_row or alt_row.group_id != sender_row.group_id:
            return ["not_alt", False]

        if alt_row.status == self.MAIN:
            return ["remove_main", False]

        self.db.exec("DELETE FROM alts WHERE char_id = ?", [alt_char_id])
        return ["success", True]

    def get_alt_status(self, char_id):
        return self.db.query_single("SELECT group_id, status FROM alts WHERE char_id = ?", [char_id])

    def get_next_group_id(self):
        row = self.db.query_single("SELECT (COALESCE(MAX(group_id), 0) + 1) AS next_group_id FROM alts")
        return row.next_group_id

    def get_main(self, char_id):
        return self.get_alts(char_id).pop(0)
