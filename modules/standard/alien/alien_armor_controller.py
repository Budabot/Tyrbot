import math

import hjson

from core.chat_blob import ChatBlob
from core.command_param_types import Options, Int
from core.decorators import instance, command
from core.text import Text
from core.translation_service import TranslationService
from modules.standard.items.items_controller import ItemsController


@instance()
class AlienArmorController:
    def inject(self, registry):
        self.text: Text = registry.get_instance("text")
        self.items_controller: ItemsController = registry.get_instance("items_controller")
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.getresp = self.ts.get_response

    def start(self):
        self.init_static_items()
        self.ts.register_translation("module/alien", self.load_alien_msg)

    def load_alien_msg(self):
        with open("modules/standard/alien/alien.msg", mode="r", encoding="utf-8") as f:
            return hjson.load(f)

    @command(command="aiarmor", params=[], access_level="all",
             description="List the alien armor types")
    def aiarmor_list_command(self, request):
        blob = self.getresp("module/alien", "ai_armor", {
            "strong": self.text.make_tellcmd("Strong Armor", "aiarmor Strong"),
            "supple": self.text.make_tellcmd("Supple Armor", "aiarmor Supple"),
            "enduring": self.text.make_tellcmd("Enduring Armor", "aiarmor Enduring"),
            "observant": self.text.make_tellcmd("Observant Armor", "aiarmor Observant"),
            "arithmetic": self.text.make_tellcmd("Arithmetic Armor", "aiarmor Arithmetic"),
            "spiritual": self.text.make_tellcmd("Spiritual Armor", "aiarmor Spiritual"),
            "cc": self.text.make_tellcmd("Combined Commando's Armor", "aiarmor cc"),
            "cm": self.text.make_tellcmd("Combined Mercenary's Armor", "aiarmor cm"),
            "co": self.text.make_tellcmd("Combined Officer's", "aiarmor co"),
            "cp": self.text.make_tellcmd("Combined Paramedic's Armor", "aiarmor cp"),
            "cs": self.text.make_tellcmd("Combined Scout's Armor", "aiarmor cs"),
            "css": self.text.make_tellcmd("Combined Sharpshooter's Armor", "aiarmor css")
        })

        return ChatBlob(self.getresp("module/alien", "ai_armor_title"), blob)

    @command(command="aiarmor",
             params=[Options(["strong", "supple", "enduring", "observant", "arithmetic", "spiritual"]),
                     Int("ql", is_optional=True)], access_level="all",
             description="Show the process for making normal alien armor")
    def aiarmor_normal_command(self, request, armor_type, ql):
        armor_type = armor_type.capitalize()
        ql = ql or 300
        misc_ql = math.floor(ql * 0.8)

        blob = self.getresp("module/alien", "ai_armor_ts", {
            "armor_type": armor_type,
            "ql": ql,
            **self.get_static_items(),
            **self.text.generate_item(self.items_controller.find_by_name("Kyr'Ozch Viralbots"), misc_ql, "viralbots"),
            **self.text.generate_item(self.items_controller.find_by_name("Memory-Wiped Kyr'Ozch Viralbots"), misc_ql, "memory_wiped_viralbots"),
            "step1_CL": math.ceil(misc_ql * 4.5),
            "step1_NP": math.ceil(misc_ql * 4.5),

            **self.text.generate_item(self.items_controller.find_by_name("Formatted Kyr'Ozch Viralbots"), misc_ql, "formatted_viralbots"),
            "step2_CL": math.ceil(misc_ql * 4.5),
            "step2_NP": math.ceil(misc_ql * 6),

            **self.text.generate_item(self.items_controller.find_by_name("Solid Clump of Kyr'Ozch Bio-Material"), ql, "solid_clump"),
            **self.text.generate_item(self.items_controller.find_by_name("Mutated Kyr'Ozch Bio-Material"), ql, "mutated_material"),
            **self.text.generate_item(self.items_controller.find_by_name("Pristine Kyr'Ozch Bio-Material"), ql, "pristine_material"),
            "step3_chem": math.ceil(ql * 4.5),

            **self.text.generate_item(self.items_controller.find_by_name("Generic Kyr'Ozch DNA-Soup"), ql, "dna_soup"),
            "chem_prist": math.ceil(ql * 4.5),
            "chem_mutat": math.ceil(ql * 7),

            **self.text.generate_item(self.items_controller.find_by_name("DNA Cocktail"), ql, "dna_cocktail"), "pharma": math.ceil(ql * 6),

            **self.text.generate_item(self.items_controller.find_by_name("Kyr'Ozch Formatted Viralbot Solution"), ql, "formatted_viralbot_solution"),
            **self.text.generate_item(self.items_controller.find_by_name("Formatted Viralbot Vest"), ql, "formatted_viralbot_vest"),
            "psycho": math.floor(ql * 6),
            **self.get_armor(armor_type, ql),
        })

        return ChatBlob(self.getresp("module/alien", "ai_armor_ts_title", {"ql": ql, "name": armor_type}), blob)

    def get_armor(self, armor_type, ql):
        blob = None
        bot_ql = math.floor(ql * 0.8)
        armor = self.items_controller.find_by_name("%s Body Armor" % armor_type, ql)
        bot = self.items_controller.find_by_name("%s Lead Viralbots" % armor_type, bot_ql)
        return {"icon_armor": self.text.make_item(armor.lowid, armor.highid, ql, self.text.make_image(armor.icon)),
                "text_armor": self.text.make_item(armor.lowid, armor.highid, ql, armor.name),
                "icon_vb_bot": self.text.make_item(bot.lowid, bot.highid, bot_ql, self.text.make_image(bot.icon)),
                "text_vb_bot": self.text.make_item(bot.lowid, bot.highid, bot_ql, bot.name),
                "vb_ql": bot_ql
                }

    @command(command="aiarmor",
             params=[Options(["cc", "cm", "co", "cp", "cs", "css", "ss"]), Int("ql", is_optional=True)],
             access_level="all",
             description="Show the process for making combined alien armor",
             extended_description="CSS and SS both refer to Combined Sharpshooters")
    def aiarmor_combined_command(self, request, armor_type, target_ql):
        armor_type = armor_type.lower()
        target_ql = target_ql or 300
        source_ql = math.floor(target_ql * 0.8)

        if armor_type == "cc":
            result_armor_id = 246660  # Combined Commando's Jacket

            source_armor_id = 246616  # Strong Body Armor
            name_source = "strong"

            target_armor_id = 246622  # Supple Body Armor
            name_target = "supple"
        elif armor_type == "cm":
            result_armor_id = 246638  # Combined Mercenary's Jacket

            source_armor_id = 246616  # Strong Body Armor
            name_source = "strong"

            target_armor_id = 246580  # Enduring Body Armor
            name_target = "enduring"
        elif armor_type == "co":
            result_armor_id = 246672  # Combined Officer's Jacket

            source_armor_id = 246600  # Spiritual Body Armor
            name_source = "spiritual"

            target_armor_id = 246560  # Arithmetic Body Armor
            name_target = "arithmetic"
        elif armor_type == "cp":
            result_armor_id = 246648  # Combined Paramedic's Jacket

            source_armor_id = 246600  # Spiritual Body Armor
            name_source = "spiritual"

            target_armor_id = 246580  # Enduring Body Armor
            name_target = "enduring"
        elif armor_type == "cs":
            result_armor_id = 246684  # Combined Scout's Jacket

            source_armor_id = 246592  # Observant Body Armor
            name_source = "observant"

            target_armor_id = 246560  # Arithmetic Body Armor
            name_target = "arithmetic"
        elif armor_type == "css" or armor_type == "ss":
            result_armor_id = 246696  # Combined Sharpshooter's Jacket

            source_armor_id = 246592  # Observant Body Armor
            name_source = "observant"

            target_armor_id = 246622  # Supple Body Armor
            name_target = "supple"
        else:
            return self.getresp("module/alien", "ai_armor_combined_unknown", {"type": armor_type})

        source = self.items_controller.get_by_item_id(source_armor_id)
        target = self.items_controller.get_by_item_id(target_armor_id)
        result = self.items_controller.get_by_item_id(result_armor_id)

        blob = self.getresp("module/alien", "ai_armor_combined", {
            **self.text.generate_item(source, source_ql, "source"),
            "s_ql": source_ql,
            "t_ql": target_ql,
            "ts_process_source": self.text.make_tellcmd(self.getresp("module/alien", "ai_armor_ts_process"),
                                                        "aiarmor %s %d" % (name_source, source_ql)),
            **self.text.generate_item(target, target_ql, "target"),
            "ts_process_target": self.text.make_tellcmd(self.getresp("module/alien", "ai_armor_ts_process"),
                                                        "aiarmor %s %d" % (name_target, target_ql)),
            **self.text.generate_item(result, target_ql, "result")})

        return ChatBlob(
            self.getresp("module/alien", "ai_armor_combined_title", {"ql": target_ql, "type": result.name}), blob)

    def get_static_items(self):
        return self.static_items

    def init_static_items(self):
        self.static_items = {
            **self.text.generate_item(
                self.items_controller.find_by_name("Kyr'Ozch Atomic Re-Structuralizing Tool", 100), 100, "step1_tool"),
            **self.text.generate_item(self.items_controller.find_by_name("Nano Programming Interface", 1), 1, "NPI"),
            **self.text.generate_item(self.items_controller.find_by_name("Kyr'Ozch Structural Analyzer", 100), 100,
                                      "structural_analyser"),
            **self.text.generate_item(self.items_controller.find_by_name("Uncle Bazzit's Generic Nano-Solvent", 100),
                                      100, "bazzit_generic_nano_solvent"),
            **self.text.generate_item(self.items_controller.find_by_name("Essential Human DNA", 100), 100, "human_dna"),
            **self.text.generate_item(self.items_controller.find_by_name("Basic Fashion Vest", 1), 1,
                                      "basic_fashion_vest"),
        }
