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

    @command(command="ofabweapons", params=[], access_level="all",
             description="Show ofab weapons")
    def ofabweapons_list_command(self, channel, sender, reply, args):
        data = self.db.query("SELECT type, name FROM ofab_weapons ORDER BY name ASC")

        blob = ""
        for row in data:
            blob += "<pagebreak>%s - Type %d\n" % (self.text.make_chatcmd(row.name, "/tell <myname> ofabweapons %s" % row.name), row.type)

        reply(ChatBlob("Ofab Weapons", blob))

    @command(command="ofabweapons", params=[Any("weapon"), Int("ql", is_optional=True)], access_level="all",
             description="Show info about an ofab weapon")
    def ofabweapons_show_command(self, channel, sender, reply, args):
        weapon_name = args[0].capitalize()
        ql = args[1] or 300

        weapon = self.db.query_single("SELECT type, vp FROM ofab_weapons w, ofab_weapons_cost c WHERE w.name LIKE ? AND c.ql = ?", [weapon_name, ql])

        if not weapon:
            reply("Could not find ofab weapon <highlight>%s<end>." % weapon_name)
            return

        type_ql = round(ql * 0.8)
        type_link = self.text.make_chatcmd("Kyr'Ozch Bio-Material - Type %d" % weapon.type, "/tell <myname> bioinfo %d %d" % (weapon.type, type_ql))

        blob = "Upgrade with %s (minimum QL %d)\n\n" % (type_link, type_ql)

        data = self.db.query("SELECT ql FROM ofab_weapons_cost ORDER BY ql ASC")
        for row in data:
            blob += self.text.make_chatcmd(row.ql, "/tell <myname> ofabweapons %s %d" % (weapon_name, row.ql)) + " "
        blob += "\n\n"

        for i in range(1, 7):
            item = self.items_controller.find_by_name("Ofab %s Mk %d" % (weapon_name, i))
            blob += "<pagebreak>" + self.text.format_item(item)
            if i == 1:
                blob += "  (<highlight>%d<end> VP)" % weapon.vp
            blob += "\n"

        reply(ChatBlob("Ofab %s (QL %d)" % (weapon_name, ql), blob))
