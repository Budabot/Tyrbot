from core.chat_blob import ChatBlob
from core.command_param_types import Any, Int
from core.decorators import instance, command
from core.text import Text


@instance()
class OfabArmorController:
    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.util = registry.get_instance("util")

    def pre_start(self):
        self.db.load_sql_file(self.module_dir + "/" + "ofab_armor.sql")

    @command(command="ofabarmor", params=[], access_level="all",
             description="Show ofab armor")
    def ofabarmor_list_command(self, request):
        data = self.db.query("SELECT type, profession FROM ofab_armor_type ORDER BY profession ASC")

        blob = ""
        for row in data:
            blob += "<pagebreak>%s - Type %d\n" % (self.text.make_tellcmd(row.profession, "ofabarmor %s" % row.profession), row.type)

        return ChatBlob("Ofab Armor", blob)

    @command(command="ofabarmor", params=[Int("ql", is_optional=True), Any("profession"), Int("ql", is_optional=True)], access_level="all",
             description="Show info about ofab armor", extended_description="QL is optional and can come before or after the profession")
    def ofabarmor_show_command(self, request, ql1, prof_name, ql2):
        profession = self.util.get_profession(prof_name)
        ql = ql1 or ql2 or 300

        if not profession:
            return "Could not find Ofab Armor for profession <highlight>%s</highlight>." % prof_name

        data = self.db.query("SELECT * FROM ofab_armor o1 LEFT JOIN ofab_armor_cost o2 ON o1.slot = o2.slot WHERE o1.profession = ? AND o2.ql = ? ORDER BY upgrade ASC, name ASC",
                             [profession, ql])
        if not data:
            return "Could not find Ofab Armor for QL <highlight>%d</highlight>." % ql

        upgrade_type = self.db.query_single("SELECT type FROM ofab_armor_type WHERE profession = ?", [profession]).type

        type_ql = round(ql * 0.8)
        type_link = self.text.make_tellcmd("Kyr'Ozch Bio-Material - Type %d" % upgrade_type, "bioinfo %d %d" % (upgrade_type, type_ql))

        blob = "Upgrade with %s (minimum QL %d)\n\n" % (type_link, type_ql)

        cost_data = self.db.query("SELECT DISTINCT ql FROM ofab_weapons_cost ORDER BY ql ASC")
        for row in cost_data:
            blob += self.text.make_tellcmd(row.ql, "ofabarmor %s %d" % (profession, row.ql)) + " "
        blob += "\n\n"

        current_upgrade = ""
        total_vp = 0
        for row in data:
            if current_upgrade != row.upgrade:
                current_upgrade = row.upgrade
                blob += "\n"

            blob += "<pagebreak>" + self.text.make_item(row.lowid, row.highid, ql, row.name)

            if row.upgrade == 0 or row.upgrade == 3:
                blob += "  (<highlight>%d</highlight> VP)" % row.vp
                total_vp += row.vp
            blob += "\n"

        blob += "\nVP cost for full set: <highlight>%d</highlight>" % total_vp

        return ChatBlob("%s Ofab Armor (QL %d)" % (profession, ql), blob)
