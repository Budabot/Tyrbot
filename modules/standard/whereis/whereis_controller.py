from core.decorators import instance, command
from core.text import Text
from core.command_param_types import Any
from core.chat_blob import ChatBlob


@instance()
class WhereisController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")

    @command(command="whereis", params=[Any("search")], access_level="all",
             description="Find locations of NPCs and places")
    def handle_whereis_cmd(self, channel, sender, reply, args):
        search = args[0]
        data = self.search_whereis(search)

        count = len(data)
        if count > 0:
            blob = ""
            for row in data:
                blob += "<pagebreak><header2>" + row.name + "<end>\n" + row.answer
                if row.playfield_id and row.xcoord and row.ycoord:
                    blob += " " + self.text.make_chatcmd("waypoint: %sx%s %s" % (row.xcoord, row.ycoord, row.short_name),
                                                         "/waypoint %s %s %d" % (row.xcoord, row.ycoord, row.playfield_id))
                blob += "\n\n"
            reply(ChatBlob("Whereis '%s' (%d)" % (search, count), blob, "this is a footer"))
        else:
            reply("Could not find any results for your search.")

    def search_whereis(self, search):
        return self.db.query(
            *self.db.handle_extended_like("SELECT w.playfield_id, w.name, w.answer, w.xcoord, w.ycoord, p.short_name FROM whereis w "
                                          "LEFT JOIN playfields p ON w.playfield_id = p.id "
                                          "WHERE name <EXTENDED_LIKE=0> ? OR keywords <EXTENDED_LIKE=1> ?",
                                          [search, search]))
