from core.command_param_types import Any, Int, NamedParameters
from core.decorators import instance, command
from core.chat_blob import ChatBlob


@instance()
class NanoController:
    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.text = registry.get_instance("text")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("nl", "nanolines")
        self.command_alias_service.add_alias("nanoline", "nanolines")

    @command(command="nano", params=[Any("search"), NamedParameters(["page"])], access_level="all",
             description="Search for a nano")
    def nano_cmd(self, request, search, named_params):
        page = int(named_params.page or "1")
        page_size = 30
        offset = (page - 1) * page_size

        sql = "SELECT n1.lowid, n1.lowql, n1.name, n1.location, n1.profession, n3.id AS nanoline_id, n3.name AS nanoline_name " \
              "FROM nanos n1 " \
              "LEFT JOIN nanos_nanolines_ref n2 ON n1.lowid = n2.lowid " \
              "LEFT JOIN nanolines n3 ON n2.nanolines_id = n3.id " \
              "WHERE n1.name <EXTENDED_LIKE=0> ? " \
              "ORDER BY n1.profession, n3.name, n1.lowql DESC, n1.name ASC"
        data = self.db.query(sql, [search], extended_like=True)
        count = len(data)
        paged_data = data[offset:offset + page_size]

        blob = ""

        if count == 1:
            row = data[0]
            return self.format_single_nano(row)
        if count > page_size:
            if page > 1 and len(paged_data) > 0:
                blob += "   " + self.text.make_chatcmd("<< Page %d" % (page - 1), self.get_chat_command(search, page - 1))
            if offset + page_size < len(data):
                blob += "   Page " + str(page)
                blob += "   " + self.text.make_chatcmd("Page %d >>" % (page + 1), self.get_chat_command(search, page + 1))
            blob += "\n\n"

        current_nanoline = -1
        for row in paged_data:
            if current_nanoline != row.nanoline_id:
                if row.nanoline_name:
                    blob += "\n<header2>%s</header2> - %s\n" % (row.profession, self.text.make_chatcmd(row.nanoline_name, "/tell <myname> nanolines %d" % row.nanoline_id))
                else:
                    blob += "\n<header2>Unknown/General</header2>\n"
                current_nanoline = row.nanoline_id

            blob += "%s [%d] %s\n" % (self.text.make_item(row.lowid, row.lowid, row.lowql, row.name), row.lowql, row.location)
        blob += self.get_footer()

        return ChatBlob("Nano Search Results for '%s' (%d - %d of %d)" % (search, offset + 1, min(offset + page_size, count), count), blob)
        
    def format_single_nano(self, row):
        msg =  " %s %s <highlight>%s</highlight> " % (self.text.make_item(row.lowid, row.lowid, row.lowql, row.name), row.location, row.nanoline_name)
        
        return msg

    @command(command="nanoloc", params=[], access_level="all",
             description="Show all nano locations")
    def nanoloc_list_cmd(self, request):
        data = self.db.query("SELECT location, COUNT(location) AS cnt FROM nanos GROUP BY location ORDER BY location ASC")

        blob = ""
        for row in data:
            blob += "%s (%d)\n" % (self.text.make_chatcmd(row.location, "/tell <myname> nanoloc %s" % row.location), row.cnt)
        blob += self.get_footer()

        return ChatBlob("Nano Locations", blob)

    @command(command="nanoloc", params=[Any("location")], access_level="all",
             description="Show nanos by location")
    def nanoloc_show_cmd(self, request, location):
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
                blob += " - <highlight>%s</highlight>" % row.profession
            blob += "\n"

        return ChatBlob("Nanos for Location '%s' (%d)" % (location, cnt), blob)

    @command(command="nanolines", params=[], access_level="all",
             description="Show nanos by nanoline")
    def nanolines_list_cmd(self, request):
        data = self.db.query("SELECT DISTINCT profession FROM nanolines ORDER BY profession ASC")

        blob = ""
        for row in data:
            blob += self.text.make_chatcmd(row.profession, "/tell <myname> nanolines %s" % row.profession) + "\n"
        blob += self.get_footer()

        return ChatBlob("Nanolines", blob)

    @command(command="nanolines", params=[Int("nanoline_id")], access_level="all",
             description="Show nanos by nanoline id")
    def nanolines_id_cmd(self, request, nanoline_id):
        nanoline = self.db.query_single("SELECT * FROM nanolines WHERE id = ?", [nanoline_id])

        if not nanoline:
            return "Could not find nanoline with ID <highlight>%d</highlight>." % nanoline_id

        data = self.db.query("SELECT n1.lowid, n1.lowql, n1.name, n1.location "
                             "FROM nanos n1 JOIN nanos_nanolines_ref n2 ON n1.lowid = n2.lowid "
                             "WHERE n2.nanolines_id = ? "
                             "ORDER BY n1.lowql DESC, n1.name ASC", [nanoline_id])

        blob = ""
        for row in data:
            blob += "%s [%d] %s\n" % (self.text.make_item(row.lowid, row.lowid, row.lowql, row.name), row.lowql, row.location)
        blob += self.get_footer()

        return ChatBlob("%s %s Nanos" % (nanoline.profession, nanoline.name), blob)

    @command(command="nanolines", params=[Any("profession")], access_level="all",
             description="Show nanolines by profession")
    def nanolines_profession_cmd(self, request, prof_name):
        profession = self.util.get_profession(prof_name)
        if not profession:
            return "Could not find profession <highlight>%s</highlight>." % prof_name

        data = self.db.query("SELECT * FROM nanolines WHERE profession = ? ORDER BY name ASC", [profession])

        blob = ""
        for row in data:
            blob += self.text.make_chatcmd(row.name, "/tell <myname> nanolines %d" % row.id) + "\n"
        blob += self.get_footer()

        return ChatBlob("%s Nanolines" % profession, blob)

    def get_footer(self):
        return "\n\nNanos DB provided by Saavick & Lucier"

    def get_chat_command(self, search, page):
        return "/tell <myname> nano %s --page=%d" % (search, page)
