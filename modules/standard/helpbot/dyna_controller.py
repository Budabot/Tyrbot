from core.decorators import instance, command
from core.command_param_types import Int, Any
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob
import math


@instance()
class DynaController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")

    @command(command="dyna", params=[], access_level="all",
             description="Show a list of dyna mob types")
    def dyna_mob_types_command(self, request):
        data = self.db.query("SELECT mob, MIN(minQl) AS minQl, MAX(maxQl) AS maxQl FROM dynadb GROUP BY mob ORDER BY mob ASC")

        blob = ""
        for row in data:
            blob += "%s (%d - %d)\n" % (self.text.make_chatcmd(row.mob, "/tell <myname> dyna %s" % row.mob), row.minQl, row.maxQl)

        return ChatBlob("Dyna Mobs (%d)" % len(data), blob)

    @command(command="dyna", params=[Int("level")], access_level="all",
             description="Show a list of dyna camps +/- 25 of QL")
    def dyna_level_command(self, request, level):
        min_level = level - 25
        max_level = level + 25

        data = self.db.query("SELECT * FROM dynadb d JOIN playfields p ON d.playfield_id = p.id WHERE d.minQl >= ? AND d.maxQl <= ? ORDER BY minQl", [min_level, max_level])

        blob = "Results of dyna camps between QL <highlight>%d</highlight> and <highlight>%d</highlight>\n\n" % (min_level, max_level)
        blob += self.format_results(data)
        url = "http://creativestudent.com/ao/files-helpfiles.html"
        blob += "Dyna camp information taken from CSP help files: " + self.text.make_chatcmd(url, "/start " + url)

        return ChatBlob("Dyna Camps (%d)" % len(data), blob)

    @command(command="dyna", params=[Any("search")], access_level="all",
             description="Search for dyna camps based on playfield or mob type")
    def dyna_search_command(self, request, search):
        search_param = "%" + search + "%"
        data = self.db.query("SELECT * FROM dynadb d JOIN playfields p ON d.playfield_id = p.id "
                             "WHERE p.long_name LIKE ? OR p.short_name LIKE ? OR d.mob LIKE ? ORDER BY d.minQl",
                             [search_param, search_param, search_param])

        blob = "Results of dyna camps search for <highlight>%s</highlight>\n\n" % search
        blob += self.format_results(data)
        url = "http://creativestudent.com/ao/files-helpfiles.html"
        blob += "Dyna camp information taken from CSP help files: " + self.text.make_chatcmd(url, "/start " + url)

        return ChatBlob("Dyna Camps (%d)" % len(data), blob)

    def format_results(self, data):
        blob = ""
        for row in data:
            coordinates = self.text.make_chatcmd("%s %dx%d" % (row.long_name, row.cX, row.cY), "/waypoint %d %d %d" % (row.cX, row.cY, row.playfield_id))
            blob += "<pagebreak>" + coordinates + "\n"
            blob += "%s - Level <highlight>%d-%d</highlight>\n\n" % (row.mob, row.minQl, row.maxQl)
        return blob
