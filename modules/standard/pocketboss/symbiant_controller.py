from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.command_param_types import Any


@instance()
class SymbiantController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("symb", "symbiant")
        self.command_alias_service.add_alias("symbs", "symbiant")
        self.command_alias_service.add_alias("symbiants", "symbiant")

    @command(command="symbiant", params=[Any("search")], access_level="all",
             description="Show information about symbiants")
    def symbiant_cmd(self, request, search):
        data = self.search_for_symbiant(search)

        blob = ""
        for row in data:
            blob += "%s (%d)\n" % (self.text.make_item(row.lowid, row.highid, row.highql, row.name), row.highql)
            blob += "Found on %s\n\n" % self.text.make_chatcmd(row.pocketboss_name, "/tell <myname> pocketboss %s" % row.pocketboss_name)

        return ChatBlob("Symbiant Search Results (%d)" % len(data), blob)

    def search_for_symbiant(self, search):
        parts = " ".join((map(self.replacements, search.split(" "))))

        return self.db.query("SELECT a.*, p2.name AS pocketboss_name FROM pocketboss_loot p "
                             "LEFT JOIN aodb a ON p.item_id = a.highid "
                             "LEFT JOIN pocketboss p2 ON p.pocketboss_id = p2.id "
                             "WHERE a.name <EXTENDED_LIKE=0> ? "
                             "ORDER BY a.highql DESC, a.name ASC", [parts], extended_like=True)

    def replacements(self, part):
        if part == "eye":
            return "ocular"
        elif part == "head":
            return "brain"
        elif part == "rarm":
            return "right arm"
        elif part == "larm":
            return "left arm"
        elif part == "rwrist":
            return "right wrist"
        elif part == "lwrist":
            return "left wrist"
        elif part == "rhand":
            return "right hand"
        elif part == "lhand":
            return "left hand"
        elif part == "leg" or part == "legs":
            return "thigh"
        else:
            return part
