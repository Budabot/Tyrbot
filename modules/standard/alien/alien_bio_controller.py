from core.chat_blob import ChatBlob
from core.command_param_types import Any, Item, Int
from core.decorators import instance, command
from core.text import Text
import math


@instance()
class AlienBioController:
    def __init__(self):
        self.ofab_armor_types = ["64", "295", "468", "935"]
        self.ofab_weapon_types = ["18", "34", "687", "812"]
        self.alien_armor_types = ["mutated", "pristine"]
        self.alien_weapon_types = ["1", "2", "3", "4", "5", "12", "13", "48", "76", "112", "240", "880", "992"]

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.items_controller = registry.get_instance("items_controller")

    @command(command="bio", params=[Item("bio_material")], access_level="all",
             description="Show info about Kyr'Ozch Bio-Material")
    def bio_command(self, channel, sender, reply, item):
        high_id = item.high_id
        ql = item.ql

        if high_id == 247707 or high_id == 247708:
            bio_type = "1"
        elif high_id == 247709 or high_id == 247710:
            bio_type = "2"
        elif high_id == 247717 or high_id == 247718:
            bio_type = "3"
        elif high_id == 247711 or high_id == 247712:
            bio_type = "4"
        elif high_id == 247713 or high_id == 247714:
            bio_type = "5"
        elif high_id == 247715 or high_id == 247716:
            bio_type = "12"
        elif high_id == 247719 or high_id == 247720:
            bio_type = "13"
        elif high_id == 288699 or high_id == 288700:
            bio_type = "48"
        elif high_id == 247697 or high_id == 247698:
            bio_type = "76"
        elif high_id == 247699 or high_id == 247700:
            bio_type = "112"
        elif high_id == 247701 or high_id == 247702:
            bio_type = "240"
        elif high_id == 247703 or high_id == 247704:
            bio_type = "880"
        elif high_id == 247705 or high_id == 247706:
            bio_type = "992"
        elif high_id == 247102 or high_id == 247103:
            bio_type = "pristine"
        elif high_id == 247104 or high_id == 247105:
            bio_type = "mutated"
        elif high_id == 247764 or high_id == 254804:
            bio_type = "serum"
        else:
            bio_type = "unknown"

        bio_info = self.get_bio_info(bio_type, ql)
        if bio_info:
            return bio_info
        else:
            return "Bio-Material type unknown or not a bio-material."

    @command(command="bioinfo", params=[], access_level="all",
             description="Show list of Kyr'Ozch Bio-Material types")
    def bioinfo_list_command(self, channel, sender, reply):
        blob = "<header2>OFAB Armor Types<end>\n"
        blob += self.get_type_blob(self.ofab_armor_types)

        blob += "\n<header2>OFAB Weapon Types<end>\n"
        blob += self.get_type_blob(self.ofab_weapon_types)

        blob += "\n<header2>AI Armor Types<end>\n"
        blob += self.get_type_blob(self.alien_armor_types)

        blob += "\n<header2>AI Weapon Types<end>\n"
        blob += self.get_type_blob(self.alien_weapon_types)

        blob += "\n<header2>Serum<end>\n"
        blob += self.get_type_blob(["serum"])

        return ChatBlob("Bio-Material Types", blob)

    def get_type_blob(self, bio_types):
        blob = ""
        for bio_type in bio_types:
            blob += self.text.make_chatcmd(bio_type, "/tell <myname> bioinfo %s" % bio_type) + "\n"
        return blob

    @command(command="bioinfo", params=[Any("bio_type"), Int("ql", is_optional=True)], access_level="all",
             description="Show info about a bio-material type")
    def bioinfo_show_command(self, channel, sender, reply, bio_type, ql):
        ql = ql or 300

        bio_info = self.get_bio_info(bio_type, ql)
        if bio_info:
            return bio_info
        else:
            return "Unknown bio-material type <highlight>%s<end>." % bio_type

    def get_bio_info(self, bio_type, ql):
        if bio_type in self.ofab_armor_types:
            return self.ofab_armor_bio(bio_type, ql)
        elif bio_type in self.ofab_weapon_types:
            return self.ofab_weapon_bio(bio_type, ql)
        elif bio_type in self.alien_armor_types:
            return self.alien_armor_bio(bio_type, ql)
        elif bio_type in self.alien_weapon_types:
            return self.alien_weapon_bio(bio_type, ql)
        elif bio_type == "serum":
            return self.serum_bio(ql)
        else:
            return None

    def ofab_armor_bio(self, bio_type, ql):
        name = "Kyr'Ozch Bio-Material - Type %s" % bio_type

        data = self.db.query("SELECT * FROM ofab_armor_type WHERE type = ?", [bio_type])

        blob = self.display_item(name, ql) + "\n\n"
        blob += "<highlight>Upgrades Ofab Armor for:<end>\n"
        for row in data:
            blob += self.text.make_chatcmd(row.profession, "/tell <myname> ofabarmor %s" % row.profession) + "\n"

        return ChatBlob("%s (QL %d)" % (name, ql), blob)

    def ofab_weapon_bio(self, bio_type, ql):
        name = "Kyr'Ozch Bio-Material - Type %s" % bio_type

        data = self.db.query("SELECT * FROM ofab_weapons WHERE type = ?", [bio_type])

        blob = self.display_item(name, ql) + "\n\n"
        blob += "<highlight>Upgrades Ofab Weapons for:<end>\n"
        for row in data:
            blob += self.text.make_chatcmd("Ofab %s Mk 1" % row.name, "/tell <myname> ofabweapons %s" % row.name) + "\n"

        return ChatBlob("%s (QL %d)" % (name, ql), blob)

    def alien_armor_bio(self, bio_type, ql):
        min_ql = math.floor(ql * 0.8)
        if ql <= 240:
            max_ql = math.floor(ql / 0.8)
        else:
            max_ql = 300

        cl = math.floor(min_ql * 4.5)
        pharma = math.floor(ql * 6)
        nano_prog = math.floor(min_ql * 6)
        psyco = math.floor(ql * 6)
        max_psyco = math.floor(max_ql * 6)
        ts_bio = math.floor(ql * 4.5)
        if bio_type == "mutated":
            name = "Mutated Kyr'Ozch Bio-Material"
            chem = math.floor(ql * 7)
            chem_msg = "7 * QL"
            extra_info = "more tradeskill requirements then pristine"
        elif bio_type == "pristine":
            name = "Pristine Kyr'Ozch Bio-Material"
            chem = math.floor(ql * 4.5)
            chem_msg = "4.5 * QL"
            extra_info = "less tradeskill requirements then mutated"
        else:
            return None

        blob = self.display_item(name, ql) + "\n\n"
        blob += "It will take <highlight>%d EE & CL<end> (<highlight>4.5 * QL<end>) to analyze the Bio-Material.\n\n" % ts_bio

        blob += "Used to build Alien Armor\n\n"
        blob += "The following tradeskill amounts are required to make <highlight>QL %d<end>\n" % ql
        blob += "strong/arithmetic/enduring/spiritual/supple/observant armor:\n\n"
        blob += "Computer Literacy - <highlight>%d<end> (<highlight>4.5 * QL<end>)\n" % cl
        blob += "Chemistry - <highlight>%d<end> (<highlight>%s<end>) %s\n" % (chem, chem_msg, extra_info)
        blob += "Nano Programming - <highlight>%d<end> (<highlight>6 * QL<end>)\n" % nano_prog
        blob += "Pharma Tech - <highlight>%d<end> (<highlight>6 * QL<end>)\n" % pharma
        blob += "Psychology - <highlight>%d<end> (<highlight>6 * QL<end>)\n\n" % psyco
        blob += "Note: Tradeskill requirements are based off the lowest QL items needed throughout the entire process."

        blob += "\n\nFor Supple, Arithmetic, or Enduring:\n\n"
        blob += "When completed, the armor piece can have as low as <highlight>QL %d<end> combined into it, depending on available tradeskill options.\n\n" % min_ql
        blob += "Does not change QL's, therefore takes <highlight>%d Psychology<end> for available combinations.<end>\n\n" % psyco
        blob += "For Spiritual, Strong, or Observant:\n\n"
        blob += "When completed, the armor piece can combine up to <highlight>QL %d<end>, depending on available tradeskill options.\n\n" % max_ql
        blob += "Changes QL depending on targets QL. "
        blob += "The max combination is: (<highlight>QL %d<end>) (<highlight>%d Psychology<end> required for this combination)" % (max_ql, max_psyco)

        blob += "\n\n<yellow>Tradeskilling info added by Mdkdoc420 (RK2)<end>"

        return ChatBlob("%s (QL %d)" % (name, ql), blob)

    def alien_weapon_bio(self, bio_type, ql):
        name = "Kyr'Ozch Bio-Material - Type %s" % bio_type

        # Ensures that the maximum AI weapon that combines into doesn't go over QL 300 when the user presents a QL 271+ bio-material
        max_ai_type = math.floor(ql / 0.9)
        if max_ai_type > 300 or max_ai_type < 1:
            max_ai_type = 300

        ts_bio = math.floor(ql * 4.5)

        blob = self.display_item(name, ql) + "\n\n"
        blob += "It will take <highlight>%d<end> EE & CL (<highlight>4.5 * QL<end>) to analyze the Bio-Material.\n\n" % ts_bio

        row = self.db.query_single("SELECT specials FROM alien_weapon_specials WHERE type = ?", [bio_type])
        blob += "<highlight>Adds %s to:<end>\n" % row.specials

        data = self.db.query("SELECT * FROM alien_weapons WHERE type = ?", [bio_type])
        for row in data:
            blob += self.display_item(row.name, max_ai_type) + "\n"

        blob += self.get_weapon_info(max_ai_type)
        blob += "\n\n<yellow>Tradeskilling info added by Mdkdoc420<end>"

        return ChatBlob("%s (QL %d)" % (name, ql), blob)

    def serum_bio(self, ql):
        name = "Kyr'Ozch Viral Serum"
        item = self.display_item(name, ql)

        pharma_ts = math.floor(ql * 3.5)
        chem_me_ts = math.floor(ql * 4)
        ee_ts = math.floor(ql * 4.5)
        cl_ts = math.floor(ql * 5)
        ts_bio = math.floor(ql * 4.5)

        if pharma_ts < 400:
            pharma_ts = 400

        if chem_me_ts < 400:
            chem_me_ts = 400

        blob = item + "\n\n"
        blob += "It will take <highlight>%d EE & CL<end> (<highlight>4.5 * QL<end>) to analyze the Bio-Material.\n\n" % ts_bio

        blob += "Used to build city buildings\n\n"
        blob += "The following are the required skills throughout the process of making a building:\n\n"
        blob += "Quantum FT - <highlight>400<end> (<highlight>Static<end>)\n"
        blob += "Pharma Tech - <highlight>%d<end> (<highlight>3.5 * QL<end>) 400 is minimum requirement\n" % pharma_ts
        blob += "Chemistry - <highlight>%d<end> (<highlight>4 * QL<end>) 400 is minimum requirement\n" % chem_me_ts
        blob += "Mechanical Engineering - <highlight>%d<end> (<highlight>4 * QL<end>)\n" % chem_me_ts
        blob += "Electrical Engineering - <highlight>%d<end> (<highlight>4.5 * QL<end>)\n" % ee_ts
        blob += "Comp Liter - <highlight>%d<end> (<highlight>5 * QL<end>)" % cl_ts

        blob += "\n\n<yellow>Tradeskilling info added by Mdkdoc420 (RK2)<end>"

        return ChatBlob("%s (QL %d)" % (name, ql), blob)

    def get_weapon_info(self, ql):
        ts_wep = math.floor(ql * 6)
        text = "\n\n<highlight>QL %d<end> is the highest weapon this type will combine into." % ql
        if ql != 300:
            text += "\nNote: <highlight>The weapon can bump several QL's.<end>"

        text += "\n\nIt will take <highlight>%d<end> ME & WS (<highlight>6 * QL<end>) to combine with a <highlight>QL %d<end> Kyr'ozch Weapon." % (ts_wep, ql)

        return text

    def display_item(self, name, ql):
        return self.text.format_item(self.items_controller.find_by_name(name, ql), ql)