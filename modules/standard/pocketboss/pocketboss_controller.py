from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.command_param_types import Any


@instance()
class PocketbossController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("pb", "pocketboss")

    @command(command="pocketboss", params=[Any("search")], access_level="all",
             description="Show information about a pocketboss")
    def pocketboss_cmd(self, request, search):
        data = self.search_for_pocketboss(search)

        num = len(data)
        if num == 1:
            row = data[0]
            blob = "Location: <highlight>%s, %s</highlight>\n" % (row.long_name, row.location)
            blob += "Found on: <highlight>%s, Level %d</highlight>\n\n" % (row.mob_type, row.level)
            symbs = self.db.query("SELECT a.* FROM pocketboss_loot p "
                                  "LEFT JOIN aodb a ON p.item_id = a.highid WHERE pocketboss_id = ? "
                                  "ORDER BY a.highql DESC, a.name ASC", [row.id])
            for symb in symbs:
                blob += "%s (%d)\n" % (self.text.make_item(symb.lowid, symb.highid, symb.highql, symb.name), symb.highql)

            return ChatBlob("Remains of %s" % row.name, blob)

        else:
            blob = ""
            for row in data:
                blob += self.text.make_chatcmd(row.name, "/tell <myname> pocketboss %s" % row.name) + "\n"

            return ChatBlob("Pocketboss Search Results (%d)" % num, blob)

    def search_for_pocketboss(self, search):
        row = self.db.query_single("SELECT p1.*, p2.long_name FROM pocketboss p1 LEFT JOIN playfields p2 ON p1.playfield_id = p2.id WHERE name LIKE ?", [search])
        if row:
            return [row]

        return self.db.query("SELECT p1.*, p2.long_name FROM pocketboss p1 LEFT JOIN playfields p2 ON p1.playfield_id = p2.id "
                             "WHERE name <EXTENDED_LIKE=0> ? ORDER BY name ASC", [search], extended_like=True)
