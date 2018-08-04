from core.command_param_types import Any
from core.decorators import instance, command
from core.chat_blob import ChatBlob


@instance()
class NanoController:
    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.text = registry.get_instance("text")

    @command(command="nano", params=[Any("search")], access_level="all",
             description="Search for a nano")
    def nano_cmd(self, channel, sender, reply, args):
        search = args[0]

        sql = "SELECT n1.lowid, n1.lowql, n1.name, n1.location, n1.profession, n3.id AS nanoline_id, n3.name AS nanoline_name " \
              "FROM nanos n1 " \
              "LEFT JOIN nanos_nanolines_ref n2 ON n1.lowid = n2.lowid " \
              "LEFT JOIN nanolines n3 ON n2.nanolines_id = n3.id " \
              "WHERE n1.name <EXTENDED_LIKE=0> ? " \
              "ORDER BY n1.profession, n3.name, n1.lowql DESC, n1.name ASC"
        data = self.db.query(*self.db.handle_extended_like(sql, [search]))
        cnt = len(data)

        blob = ""
        current_nanoline = -1
        for row in data:
            if current_nanoline != row.nanoline_id:
                if row.nanoline_name:
                    blob += "\n<header2>%s<end> - %s\n" % (row.profession, self.text.make_chatcmd(row.nanoline_name, "/tell <myname> nanolines %d" % row.nanoline_id))
                else:
                    blob += "\n<header2>Unknown/General<end>\n"
                current_nanoline = row.nanoline_id

            blob += "%s [%d] %s\n" % (self.text.make_item(row.lowid, row.lowid, row.lowql, row.name), row.lowql, row.location)
        blob += self.get_footer()

        reply(ChatBlob("Nano Search Results for '%s' (%d)" % (search, cnt), blob))

    @command(command="nanoloc", params=[], access_level="all",
             description="Show all nano locations")
    def nanoloc_list_cmd(self, channel, sender, reply, args):
        data = self.db.query("SELECT location, COUNT(location) AS cnt FROM nanos GROUP BY location ORDER BY location ASC")

        blob = ""
        for row in data:
            blob += "%s (%d)\n" % (self.text.make_chatcmd(row.location, "/tell <myname> nanoloc %s" % row.location), row.cnt)
        blob += self.get_footer()

        reply(ChatBlob("Nano Locations", blob))

    @command(command="nanoloc", params=[Any("location")], access_level="all",
             description="Show nanos by location")
    def nanoloc_show_cmd(self, channel, sender, reply, args):
        location = args[0]

        sql = "SELECT n1.lowid, n1.lowql, n1.name, n1.location, n3.profession " \
              "FROM nanos n1 LEFT JOIN nanos_nanolines_ref n2 ON n1.lowid = n2.lowid LEFT JOIN nanolines n3 ON n2.nanolines_id = n3.id " \
              "WHERE n1.location LIKE ? " \
              "ORDER BY n1.profession ASC, n1.name ASC"
        data = self.db.query(sql, [location])
        cnt = len(data)

        blob = ""
        for row in data:
            blob += "%s [%d] %s" % (self.text.make_item(row.lowid, row.lowid, row.lowql, row.name), row.lowql, row.location)
            if row.profession:
                blob += " - <highight>%s<end>" % row.profession
            blob += "\n"

        reply(ChatBlob("Nanos for Location '%s' (%d)" % (location, cnt), blob))

    def get_footer(self):
        return "\n\nNanos DB provided by Saavick & Lucier"
