import math

from core.chat_blob import ChatBlob
from core.command_param_types import Options, Int
from core.decorators import instance, command
from core.text import Text
from modules.standard.items.items_controller import ItemsController


@instance()
class AlienArmorController:
    def inject(self, registry):
        self.text: Text = registry.get_instance("text")
        self.items_controller: ItemsController = registry.get_instance("items_controller")

    @command(command="aiarmor", params=[], access_level="all",
             description="List the alien armor types")
    def aiarmor_list_command(self, request):
        blob = "<header2>Normal Armor:</header2>\n"
        blob += self.text.make_tellcmd("Strong Armor", "aiarmor Strong") + "\n"
        blob += self.text.make_tellcmd("Supple Armor", "aiarmor Supple") + "\n"
        blob += self.text.make_tellcmd("Enduring Armor", "aiarmor Enduring") + "\n"
        blob += self.text.make_tellcmd("Observant Armor", "aiarmor Observant") + "\n"
        blob += self.text.make_tellcmd("Arithmetic Armor", "aiarmor Arithmetic") + "\n"
        blob += self.text.make_tellcmd("Spiritual Armor", "aiarmor Spiritual") + "\n\n"

        blob += "<header2>Combined Armor:</header2>\n"
        blob += self.text.make_tellcmd("Combined Commando's Armor", "aiarmor cc") + "\n"
        blob += self.text.make_tellcmd("Combined Mercenary's Armor", "aiarmor cm") + "\n"
        blob += self.text.make_tellcmd("Combined Officer's", "aiarmor co") + "\n"
        blob += self.text.make_tellcmd("Combined Paramedic's Armor", "aiarmor cp") + "\n"
        blob += self.text.make_tellcmd("Combined Scout's Armor", "aiarmor cs") + "\n"
        blob += self.text.make_tellcmd("Combined Sharpshooter's Armor", "aiarmor css") + "\n"

        return ChatBlob("Alien Armor", blob)

    @command(command="aiarmor",
             params=[Options(["strong", "supple", "enduring", "observant", "arithmetic", "spiritual"]),
                     Int("ql", is_optional=True)], access_level="all",
             description="Show the process for making normal alien armor")
    def aiarmor_normal_command(self, request, armor_type, ql):
        armor_type = armor_type.capitalize()
        ql = ql or 300
        misc_ql = math.floor(ql * 0.8)

        blob = "Note: All tradeskill processes are based on the lowest QL items usable.\n\n"
        blob += "<header2>You need the following items to build %s Armor:<end>\n" % armor_type
        blob += "- Kyr'Ozch Viralbots\n"
        blob += "- Kyr'Ozch Atomic Re-Structulazing Tool\n"
        blob += "- Solid Clump of Kyr'Ozch Biomaterial\n"
        blob += "- Arithmetic/Strong/Enduring/Spiritual/Observant/Supple Viralbots\n\n"

        blob += "<header2>Step 1<end>\n"
        blob += "<tab>%s (<highlight>Drops from Alien City Generals<end>)\n" % self.display_item_by_name("Kyr'Ozch Viralbots", misc_ql)
        blob += "<tab><tab>+\n"
        blob += "<tab>%s (<highlight>Drops from every Alien<end>)\n" % self.display_item_by_name("Kyr'Ozch Atomic Re-Structuralizing Tool", 100)
        blob += "<tab><tab>=\n"
        blob += "<tab>%s\n" % self.display_item_by_name("Memory-Wiped Kyr'Ozch Viralbots", misc_ql)
        blob += "<highlight>Required Skills:<end>\n"
        blob += "- %d Computer Literacy\n" % math.ceil(misc_ql * 4.5)
        blob += "- %d Nano Programming\n\n" % math.ceil(misc_ql * 4.5)

        blob += "<header2>Step 2<end>\n"
        blob += "<tab>%s (<highlight>Can be bought in General Shops<end>)\n" % self.display_item_by_name("Nano Programming Interface", 1)
        blob += "<tab><tab>+\n"
        blob += "<tab>%s\n" % self.display_item_by_name("Memory-Wiped Kyr'Ozch Viralbots", misc_ql)
        blob += "<tab><tab>=\n"
        blob += "<tab>%s\n" % self.display_item_by_name("Formatted Kyr'Ozch Viralbots", misc_ql)
        blob += "<highlight>Required Skills:<end>\n"
        blob += "- %d Computer Literacy\n" % math.ceil(misc_ql * 4.5)
        blob += "- %d Nano Programming\n\n" % math.ceil(misc_ql * 6)

        blob += "<header2>Step 3<end>\n"
        blob += "<tab>%s\n" % self.display_item_by_name("Kyr'Ozch Structural Analyzer", 100)
        blob += "<tab><tab>+\n"
        blob += "<tab>%s QL%d (<highlight>Drops from every Alien<end>)\n" % (self.display_item_by_name("Solid Clump of Kyr'Ozch Bio-Material", ql), ql)
        blob += "<tab><tab>=\n"
        blob += "<tab>%s QL%d" % (self.display_item_by_name("Mutated Kyr'Ozch Bio-Material", ql), ql)
        blob += "\n\nor\n\n<tab>%s QL%d\n" % (self.display_item_by_name("Pristine Kyr'Ozch Bio-Material", ql), ql)
        blob += "<highlight>Required Skills:<end>\n"
        blob += "- %d Chemistry (Both require the same amount)\n\n" % math.ceil(ql * 4.5)

        blob += "<header2>Step 4<end>\n"
        blob += "<tab>%s QL%d" % (self.display_item_by_name("Mutated Kyr'Ozch Bio-Material", ql), ql)
        blob += "\n\nor\n\n<tab>%s QL%d\n" % (self.display_item_by_name("Pristine Kyr'Ozch Bio-Material", ql), ql)
        blob += "<tab><tab>+\n"
        blob += "<tab>%s (<highlight>Can be bought in Bazzit Shop in MMD<end>)\n" % self.display_item_by_name("Uncle Bazzit's Generic Nano-Solvent", 100)
        blob += "<tab><tab>=\n"
        blob += "<tab>%s\n" % self.display_item_by_name("Generic Kyr'Ozch DNA-Soup", ql)
        blob += "<highlight>Required Skills:<end>\n"
        blob += "- %d Chemistry(for Pristine)\n" % math.ceil(ql * 4.5)
        blob += "- %d Chemistry(for Mutated)\n\n" % math.ceil(ql * 7)

        blob += "<header2>Step 5<end>\n"
        blob += "<tab>" + self.display_item_by_name("Generic Kyr'Ozch DNA-Soup", ql) + "\n"
        blob += "<tab><tab>+\n"
        blob += "<tab>" + self.display_item_by_name("Essential Human DNA", 100) + " (<highlight>Can be bought in Bazzit Shop in MMD<end>)\n"
        blob += "<tab><tab>=\n"
        blob += "<tab>" + self.display_item_by_name("DNA Cocktail", ql) + "\n"
        blob += "<highlight>Required Skills:<end>\n"
        blob += "- %d Pharma Tech\n\n" % math.ceil(ql * 6)

        blob += "<header2>Step 6<end>\n"
        blob += "<tab>" + self.display_item_by_name("Formatted Kyr'Ozch Viralbots", misc_ql) + "\n"
        blob += "<tab><tab>+\n"
        blob += "<tab>" + self.display_item_by_name("DNA Cocktail", ql) + "\n"
        blob += "<tab><tab>=\n"
        blob += "<tab>" + self.display_item_by_name("Kyr'Ozch Formatted Viralbot Solution", ql) + "\n"
        blob += "<highlight>Required Skills:<end>\n"
        blob += "- %d Pharma Tech\n\n" % math.ceil(ql * 6)

        blob += "<header2>Step 7<end>\n"
        blob += "<tab>" + self.display_item_by_name("Kyr'Ozch Formatted Viralbot Solution", ql) + "\n"
        blob += "<tab><tab>+\n"
        blob += "<tab>" + self.display_item_by_name("Basic Fashion Vest", 1) + " (<highlight>Can be obtained by the Basic Armor Quest<end>)\n"
        blob += "<tab><tab>=\n"
        blob += "<tab>" + self.display_item_by_name("Formatted Viralbot Vest", ql) + "\n\n"

        blob += "<header2>Step 8<end>\n"

        vb_ql = math.floor(ql * 0.8)
        if armor_type == "Arithmetic":
            blob += "<tab>%s QL%d (<highlight>Rare Drop off Alien City Generals<end>)\n" % (self.display_item_by_name("Arithmetic Lead Viralbots", vb_ql), vb_ql)
        elif armor_type == "Supple":
            blob += "<tab>%s QL%d (<highlight>Rare Drop off Alien City Generals<end>)\n" % (self.display_item_by_name("Supple Lead Viralbots", vb_ql), vb_ql)
        elif armor_type == "Enduring":
            blob += "<tab>%s QL%d (<highlight>Rare Drop off Alien City Generals<end>)\n" % (self.display_item_by_name("Enduring Lead Viralbots", vb_ql), vb_ql)
        elif armor_type == "Observant":
            blob += "<tab>%s QL%d (<highlight>Rare Drop off Alien City Generals<end>)\n" % (self.display_item_by_name("Observant Lead Viralbots", vb_ql), vb_ql)
        elif armor_type == "Strong":
            blob += "<tab>%s QL%d (<highlight>Rare Drop off Alien City Generals<end>)\n" % (self.display_item_by_name("Strong Lead Viralbots", vb_ql), vb_ql)
        elif armor_type == "Spiritual":
            blob += "<tab>%s QL%d (<highlight>Rare Drop off Alien City Generals<end>)\n" % (self.display_item_by_name("Spiritual Lead Viralbots", vb_ql), vb_ql)

        blob += "<tab><tab>+\n"
        blob += "<tab>" + self.display_item_by_name("Formatted Viralbot Vest", ql) + "\n"
        blob += "<tab><tab>=\n"

        if armor_type == "Arithmetic":
            blob += "<tab>%s QL%d\n" % (self.display_item_by_name("Arithmetic Body Armor", ql), ql)
        elif armor_type == "Supple":
            blob += "<tab>%s QL%d\n" % (self.display_item_by_name("Supple Body Armor", ql), ql)
        elif armor_type == "Enduring":
            blob += "<tab>%s QL%d\n" % (self.display_item_by_name("Enduring Body Armor", ql), ql)
        elif armor_type == "Observant":
            blob += "<tab>%s QL%d\n" % (self.display_item_by_name("Observant Body Armor", ql), ql)
        elif armor_type == "Strong":
            blob += "<tab>%s QL%d\n" % (self.display_item_by_name("Strong Body Armor", ql), ql)
        elif armor_type == "Spiritual":
            blob += "<tab>%s QL%d\n" % (self.display_item_by_name("Spiritual Body Armor", ql), ql)

        blob += "<highlight>Required Skills:<end>\n"
        blob += "- %d Psychology\n\n" % math.floor(ql * 6)

        return ChatBlob(f"Building process for QL {ql} {armor_type}", blob)

    def get_armor(self, armor_type, ql):
        blob = None
        bot_ql = math.floor(ql * 0.8)
        armor = self.items_controller.find_by_name("%s Body Armor" % armor_type, ql)
        bot = self.items_controller.find_by_name("%s Lead Viralbots" % armor_type, bot_ql)
        return {
            "icon_armor": self.text.make_item(armor.lowid, armor.highid, ql, self.text.make_image(armor.icon)),
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
            return f"Unknown armor type <highlight>{armor_type}</highlight>."

        source = self.items_controller.get_by_item_id(source_armor_id)
        target = self.items_controller.get_by_item_id(target_armor_id)
        result = self.items_controller.get_by_item_id(result_armor_id)

        source_icon = self.text.make_image(source.icon)
        target_icon = self.text.make_image(target.icon)
        result_icon = self.text.make_image(result.icon)

        source_display = self.text.make_item(source.lowid, source.highid, source_ql, source.name)
        target_display = self.text.make_item(target.lowid, target.highid, target_ql, target.name)
        result_display = self.text.make_item(result.lowid, result.highid, target_ql, result.name)

        ts_process_source = self.text.make_tellcmd("Tradeskill process for this item", "aiarmor %s %d" % (name_source, source_ql))
        ts_process_target = self.text.make_tellcmd("Tradeskill process for this item", "aiarmor %s %d" % (name_target, target_ql))

        blob = "<header2>Tradeskill Process</header2>\n\n"
        blob += f"<tab>{source_icon}<tab>+<tab>{target_icon}<tab>=<tab>{result_icon}\n"
        blob += f"<tab>(QL{source_ql})<tab> <tab>(QL{target_ql})<tab> <tab>(QL{target_ql})\n\n"
        blob += f"<tab><tab>{source_display} (QL{source_ql}) - ({ts_process_source})\n"
        blob += f" + <tab>{target_display} (QL{target_ql}) - ({ts_process_target})\n"
        blob += f" = <tab>{result_display} (QL{target_ql})\n"

        return ChatBlob(f"Building process for QL {target_ql} {result.name}", blob)

    def display_item_by_name(self, name, ql):
        return self.text.format_item(self.items_controller.find_by_name(name, ql), ql)