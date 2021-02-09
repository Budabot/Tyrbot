from core.chat_blob import ChatBlob
from core.command_param_types import Any, Int
from core.decorators import instance, command
from core.text import Text


@instance()
class OfabWeaponsController:
    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.items_controller = registry.get_instance("items_controller")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def pre_start(self):
        self.db.load_sql_file(self.module_dir + "/" + "ofab_weapons.sql")

    def start(self):
        self.command_alias_service.add_alias("ofabweapon", "ofabweapons")

    @command(command="ofabweapons", params=[], access_level="all",
             description="Show ofab weapons")
    def ofabweapons_list_command(self, request):
        data = self.db.query("SELECT type, name FROM ofab_weapons ORDER BY name ASC")

        blob = ""
        for row in data:
            blob += "<pagebreak>%s - Type %d\n" % (self.text.make_tellcmd(row.name, "ofabweapons %s" % row.name), row.type)

        return ChatBlob("Ofab Weapons", blob)

    @command(command="ofabweapons", params=[Int("ql", is_optional=True), Any("weapon"), Int("ql", is_optional=True)], access_level="all",
             description="Show info about an ofab weapon", extended_description="QL is optional and can come before or after the weapon")
    def ofabweapons_show_command(self, request, ql1, weapon_name, ql2):
        weapon_name = weapon_name.capitalize()
        ql = ql1 or ql2 or 300

        weapon = self.db.query_single("SELECT type, vp FROM ofab_weapons w, ofab_weapons_cost c WHERE w.name LIKE ? AND c.ql = ?", [weapon_name, ql])

        if not weapon:
            return "Could not find Ofab Weapon <highlight>%s</highlight> for QL <highlight>%d</highlight>." % (weapon_name, ql)

        type_ql = round(ql * 0.8)
        type_link = self.text.make_tellcmd("Kyr'Ozch Bio-Material - Type %d" % weapon.type, "bioinfo %d %d" % (weapon.type, type_ql))

        blob = "Upgrade with %s (minimum QL %d)\n\n" % (type_link, type_ql)

        data = self.db.query("SELECT ql FROM ofab_weapons_cost ORDER BY ql ASC")
        for row in data:
            blob += self.text.make_tellcmd(row.ql, "ofabweapons %s %d" % (weapon_name, row.ql)) + " "
        blob += "\n\n"

        for i in range(1, 7):
            item = self.items_controller.find_by_name("Ofab %s Mk %d" % (weapon_name, i))
            blob += "<pagebreak>" + self.text.format_item(item)
            if i == 1:
                blob += "  (<highlight>%d</highlight> VP)" % weapon.vp
            blob += "\n"

        return ChatBlob("Ofab %s (QL %d)" % (weapon_name, ql), blob)
