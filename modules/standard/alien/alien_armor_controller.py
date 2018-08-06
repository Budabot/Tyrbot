from core.chat_blob import ChatBlob
from core.command_param_types import Options, Int
from core.decorators import instance, command
from core.text import Text
import math


@instance()
class AlienArmorController:
    def inject(self, registry):
        self.text: Text = registry.get_instance("text")
        self.items_controller = registry.get_instance("items_controller")

    @command(command="aiarmor", params=[], access_level="all",
             description="List the alien armor types")
    def aiarmor_list_command(self, channel, sender, reply, args):
        blob = ""
        blob += "<highlight>Normal Armor:<end>\n"
        blob += self.text.make_chatcmd("Strong Armor", "/tell <myname> aiarmor Strong") + "\n"
        blob += self.text.make_chatcmd("Supple Armor", "/tell <myname> aiarmor Supple") + "\n"
        blob += self.text.make_chatcmd("Enduring Armor", "/tell <myname> aiarmor Enduring") + "\n"
        blob += self.text.make_chatcmd("Observant Armor", "/tell <myname> aiarmor Observant") + "\n"
        blob += self.text.make_chatcmd("Arithmetic Armor", "/tell <myname> aiarmor Arithmetic") + "\n"
        blob += self.text.make_chatcmd("Spiritual Armor", "/tell <myname> aiarmor Spiritual") + "\n"
        blob += "\n<highlight>Combined Armor:<end>\n"
        blob += self.text.make_chatcmd("Combined Commando's Armor", "/tell <myname> aiarmor cc") + "\n"
        blob += self.text.make_chatcmd("Combined Mercenary's Armor", "/tell <myname> aiarmor cm") + "\n"
        blob += self.text.make_chatcmd("Combined Officer's", "/tell <myname> aiarmor co") + "\n"
        blob += self.text.make_chatcmd("Combined Paramedic's Armor", "/tell <myname> aiarmor cp") + "\n"
        blob += self.text.make_chatcmd("Combined Scout's Armor", "/tell <myname> aiarmor cs") + "\n"
        blob += self.text.make_chatcmd("Combined Sharpshooter's Armor", "/tell <myname> aiarmor css")

        return ChatBlob("Alien Armor", blob)

    @command(command="aiarmor", params=[Options(["strong", "supple", "enduring", "observant", "arithmetic", "spiritual"]), Int("ql", is_optional=True)], access_level="all",
             description="Show the process for making normal alien armor")
    def aiarmor_normal_command(self, channel, sender, reply, args):
        armor_type = args[0].capitalize()
        ql = args[1] or 300
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

        return ChatBlob("Building process for %d %s" % (ql, armor_type), blob)

    @command(command="aiarmor", params=[Options(["cc", "cm", "co", "cp", "cs", "css", "ss"]), Int("ql", is_optional=True)], access_level="all",
             description="Show the process for making combined alien armor", extended_description="CSS and SS both refer to Combined Sharpshooters")
    def aiarmor_combined_command(self, channel, sender, reply, args):
        armor_type = args[0]
        target_ql = args[1] or 300
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
            reply("Unknown armor type <highlight>%s<end>" % armor_type)
            return

        result_item = self.items_controller.get_by_item_id(result_armor_id)

        blob = "<header2>Result<end>\n"
        blob += "%s QL%d\n\n" % (self.text.format_item(result_item, target_ql), target_ql)

        blob += "<header2>Source Armor<end>\n"
        blob += "%s QL%d" % (self.text.format_item(self.items_controller.get_by_item_id(source_armor_id), target_ql), source_ql)
        blob += " (%s)\n\n" % self.text.make_chatcmd("Tradeskill process for this item", "/tell <myname> aiarmor %s %d" % (name_source, source_ql))

        blob += "<header2>Target Armor<end>\n"
        blob += "%s QL%d" % (self.text.format_item(self.items_controller.get_by_item_id(target_armor_id), target_ql), target_ql)
        blob += " (%s)" % self.text.make_chatcmd("Tradeskill process for this item", "/tell <myname> aiarmor %s %d" % (name_target, target_ql))

        return ChatBlob("Building process for %d %s" % (target_ql, result_item.name), blob)

    def display_item_by_name(self, name, ql):
        return self.text.format_item(self.items_controller.find_by_name(name, ql), ql)
