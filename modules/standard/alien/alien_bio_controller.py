import math

from core.chat_blob import ChatBlob
from core.command_param_types import Any, Item, Int
from core.decorators import instance, command
from core.text import Text


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
        self.command_alias_service = registry.get_instance("command_alias_service")

    def pre_start(self):
        self.db.load_sql_file(self.module_dir + "/" + "alien_weapons.sql")

    def start(self):
        self.command_alias_service.add_alias("clump", "bio")

    @command(command="bio", params=[Item("bio_material")], access_level="all",
             description="Show info about Kyr'Ozch Bio-Material")
    def bio_command(self, request, item):
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
    def bioinfo_list_command(self, request):
        blob = "\n<header2>OFAB Armor Types</header2>\n"
        blob += self.get_type_blob(self.ofab_armor_types)
        blob += "\n<header2>OFAB Weapon Types</header2>\n"
        blob += self.get_type_blob(self.ofab_weapon_types)
        blob += "\n<header2>AI Armor Types</header2>\n"
        blob += self.get_type_blob(self.alien_armor_types)
        blob += "\n<header2>AI Weapon Typen</header2>\n"
        blob += self.get_type_blob(self.alien_weapon_types)
        blob += "\n<header2>Serum Typen</header2>\n"
        blob += self.get_type_blob(["serum"])

        return ChatBlob("Bio-Material Types", blob)

    def get_type_blob(self, bio_types):
        blob = ""
        for bio_type in bio_types:
            blob += self.text.make_tellcmd(bio_type, "bioinfo %s" % bio_type) + "\n"
        return blob

    @command(command="bioinfo", params=[Any("bio_type"), Int("ql", is_optional=True)], access_level="all",
             description="Show info about a bio-material type")
    def bioinfo_show_command(self, request, bio_type, ql):
        ql = ql or 300

        bio_info = self.get_bio_info(bio_type, ql)
        if bio_info:
            return bio_info
        else:
            return f"Unknown bio-material type <highlight>{bio_type}</highlight>."

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

        blob = self.display_item(name, ql) +  "\n\n"
        blob += "<highlight>Upgrades Ofab Armor for:</highlight>\n"

        data = self.db.query("SELECT * FROM ofab_armor_type WHERE type = ?", [bio_type])
        for row in data:
            blob += self.text.make_tellcmd(row.profession, "ofabarmor %s" % row.profession) + "\n"

        return ChatBlob(f"{name} (QL {ql})", blob)

    def ofab_weapon_bio(self, bio_type, ql):
        name = "Kyr'Ozch Bio-Material - Type %s" % bio_type

        blob = self.display_item(name, ql) + "\n\n"
        blob += "<highlight>Upgrades Ofab Weapons for:</highlight>\n"

        data = self.db.query("SELECT * FROM ofab_weapons WHERE type = ?", [bio_type])
        for row in data:
            blob += self.text.make_tellcmd("Ofab %s Mk 1" % row.name, "ofabweapons %s" % row.name) + "\n"

        return ChatBlob(f"{name} (QL {ql})", blob)

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

        blob = self.display_item(name, ql) + "\n\n"

        ee_cl_req = math.floor(ql * 4.5)
        blob += f"It will take <highlight>{ee_cl_req}</highlight> EE & CL (<highlight>4.5 * QL</highlight>) to analyze the Bio-Material.\n\n"

        specials = self.db.query_single("SELECT specials FROM alien_weapon_specials WHERE type = ?", [bio_type]).specials
        blob += f"<highlight>Adds {specials} to:</highlight>\n"

        # Ensures that the maximum AI weapon that combines into doesn't go over QL 300 when the user presents a QL 271+ bio-material
        max_ai_type = math.floor(ql / 0.9)
        if max_ai_type > 300 or max_ai_type < 1:
            max_ai_type = 300

        data = self.db.query("SELECT * FROM alien_weapons WHERE type = ?", [bio_type])
        for row in data:
            blob += self.display_item(row.name, max_ai_type) + "\n"

        blob += self.get_weapon_info(max_ai_type)
        blob += "\n\n<yellow>Tradeskilling info added by Mdkdoc420</yellow>"

        return ChatBlob("%s (QL %d)" % (name, ql), blob)

    def serum_bio(self, ql):
        name = "Kyr'Ozch Viral Serum"

        ee_cl_req = math.floor(ql * 4.5),
        pt_req = (math.floor(ql * 3.5) if math.floor(ql * 3.5) > 400 else 400)
        chem_me_req = (math.floor(ql * 4) if math.floor(ql * 4) > 400 else 400)
        cl_req = math.floor(ql * 5)

        blob = self.display_item(name, ql) + "\n\n"
        blob += f"It will take <highlight>{ee_cl_req} EE & CL</highlight> (<highlight>4.5 * QL</highlight>) to analyze the Bio-Material.\n\n"
        blob += "Used to build city buildings\n\n"
        blob += "The following are the required skills throughout the process of making a building:\n\n"
        blob += "Quantum FT - <highlight>400</highlight> (<highlight>Static</highlight>)\n"
        blob += f"Pharma Tech - <highlight>{pt_req}</highlight> (<highlight>3.5 * QL</highlight>) 400 is minimum requirement\n"
        blob += f"Chemistry - <highlight>{chem_me_req}</highlight> (<highlight>4 * QL</highlight>) 400 is minimum requirement\n"
        blob += f"Mechanical Engineering - <highlight>{chem_me_req}</highlight> (<highlight>4 * QL</highlight>)\n"
        blob += f"Electrical Engineering - <highlight>{ee_cl_req}</highlight> (<highlight>4.5 * QL</highlight>)\n"
        blob += f"Comp Liter - <highlight>{cl_req}</highlight> (<highlight>5 * QL</highlight>)"
        blob += "\n\n<yellow>Tradeskilling info added by Mdkdoc420 (RK2)</yellow>"

        return ChatBlob("%s (QL %d)" % (name, ql), blob)

    def get_weapon_info(self, ql):
        msg = f"\n\n<highlight>QL {ql}</highlight> is the highest weapon this type will combine into."
        if ql != 300:
            msg += "\nNote: <highlight>The weapon can bump several QL's.</highlight>"
        msg += f"\n\nIt will take <highlight>{math.floor(ql * 6)}</highlight> ME & WS (<highlight>6 * QL</highlight>) to combine with a <highlight>QL {ql}</highlight> Kyr'ozch Weapon."

        return msg

    def display_item(self, name, ql):
        return self.text.format_item(self.items_controller.find_by_name(name, ql), ql)
