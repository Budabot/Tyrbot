import math

from core.chat_blob import ChatBlob
from core.command_param_types import Any, Item, Int
from core.decorators import instance, command
from core.text import Text
from core.translation_service import TranslationService


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
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.getresp = self.ts.get_response

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
        return ChatBlob(self.getresp("module/alien", "bioinfo_list_title"),
                        self.getresp("module/alien", "bioinfo_list", {
                            "ofab_armor": self.get_type_blob(self.ofab_armor_types),
                            "ofab_weap": self.get_type_blob(self.ofab_weapon_types),
                            "ai_armor": self.get_type_blob(self.alien_armor_types),
                            "ai_weap": self.get_type_blob(self.alien_weapon_types),
                            "serum": self.get_type_blob(["serum"]),
                        }))

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
            return self.getresp("module/alien", "bioinfo_unknown_type", {"type": bio_type})

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
        item = self.items_controller.find_by_name(name, ql)
        upgrades = ""
        for row in data:
            upgrades += self.text.make_tellcmd(row.profession, "ofabarmor %s" % row.profession) + "\n"

        return ChatBlob(self.getresp("module/alien", "bioinfo_unknown_type",
                                     {"type": bio_type, "ql": ql}),
                        self.getresp("module/alien", "ofab_armor_bio",
                                     {"type": bio_type, **self.text.generate_item(item, ql), "upgrades": upgrades}))

    def ofab_weapon_bio(self, bio_type, ql):
        name = "Kyr'Ozch Bio-Material - Type %s" % bio_type

        data = self.db.query("SELECT * FROM ofab_weapons WHERE type = ?", [bio_type])

        blob = self.display_item(name, ql) + "\n\n"
        blob += "<highlight>Upgrades Ofab Weapons for:</highlight>\n"
        for row in data:
            blob += self.text.make_tellcmd("Ofab %s Mk 1" % row.name, "ofabweapons %s" % row.name) + "\n"

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
            extra_info = self.getresp("module/alien", "alien_armor_bio_extra_info_mutated")
        elif bio_type == "pristine":
            name = "Pristine Kyr'Ozch Bio-Material"
            chem = math.floor(ql * 4.5)
            chem_msg = "4.5 * QL"
            extra_info = self.getresp("module/alien", "alien_armor_bio_extra_info_pristine")
        else:
            return None
        return ChatBlob("%s (QL %d)" % (name, ql),
                        self.getresp("module/alien", "alien_armor_bio",
                                     {"item": self.display_item(name, ql),
                                      "ee_cl_req": ts_bio, "ql": ql, "cl_req": cl, "chem_req": chem,
                                      "chem_info": chem_msg, "chem_extra_info": extra_info, "nano_prog_req": nano_prog,
                                      "pt_req": pharma, "psyco_req": psyco, "min_ql": min_ql, "max_ql": max_ql,
                                      "max_psyco": max_psyco}))

    def alien_weapon_bio(self, bio_type, ql):
        name = "Kyr'Ozch Bio-Material - Type %s" % bio_type

        # Ensures that the maximum AI weapon that combines into doesn't go over QL 300 when the user presents a QL 271+ bio-material
        max_ai_type = math.floor(ql / 0.9)
        if max_ai_type > 300 or max_ai_type < 1:
            max_ai_type = 300

        specials = self.db.query_single("SELECT specials FROM alien_weapon_specials WHERE type = ?", [bio_type]).specials
        data = self.db.query("SELECT * FROM alien_weapons WHERE type = ?", [bio_type])
        display_blob = ""
        for row in data:
            display_blob += self.display_item(row.name, max_ai_type) + "\n"

        return ChatBlob("%s (QL %d)" % (name, ql),
                        self.getresp("module/alien", "alien_weapon_bio",
                                     {"item_display": self.display_item(name, ql),
                                      "ee_cl_req": math.floor(ql * 4.5),
                                      "specials": specials,
                                      "display_blob": display_blob,
                                      "weapon_info": self.get_weapon_info(max_ai_type)
                                      }))

    def serum_bio(self, ql):
        name = "Kyr'Ozch Viral Serum"

        return ChatBlob("%s (QL %d)" % (name, ql),
                        self.getresp("module/alien", "serum_bio",
                                     {"item_display": self.display_item(name, ql),
                                      "ee_cl_req": math.floor(ql * 4.5),
                                      "pt_req": (math.floor(ql * 3.5) if math.floor(ql * 3.5) > 400 else 400),
                                      "chem_me_req": (math.floor(ql * 4) if math.floor(ql * 4) > 400 else 400),
                                      "cl_req": math.floor(ql * 5)
                                      }))

    def get_weapon_info(self, ql):
        return self.getresp("module/alien", "weapon_info",
                            {"ql": ql,
                            "bump": ("" if ql == 300 else self.getresp("module/alien", "weapon_bump")),
                             "me_ws_req": math.floor(ql * 6)})

    def display_item(self, name, ql):
        return self.text.format_item(self.items_controller.find_by_name(name, ql), ql)
