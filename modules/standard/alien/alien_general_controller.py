from core.chat_blob import ChatBlob
from core.command_param_types import Options
from core.decorators import instance, command
from core.text import Text


@instance()
class AlienGeneralController:
    def inject(self, registry):
        self.text: Text = registry.get_instance("text")
        self.items_controller = registry.get_instance("items_controller")

    @command(command="aigen", params=[], access_level="all",
             description="List alien city ground generals")
    def aigen_list_command(self, request):
        generals = ["Ankari", "Ilari", "Rimah", "Jaax", "Xoch", "Cha"]

        blob = ""
        for general in generals:
            blob += self.text.make_chatcmd(general, "/tell <myname> aigen %s" % general) + "\n"

        return ChatBlob("Alien Generals", blob)

    @command(command="aigen", params=[Options(["ankari", "ilari", "rimah", "jaax", "xoch", "cha"])], access_level="all",
             description="Show info about an alien city ground general")
    def aigen_show_command(self, request, general):
        general = general.capitalize()

        blob = ""

        if general == "Ankari":
            blob += "Low Evade/Dodge, Low AR, Casts Viral/Virral nukes\n\n"
            blob += self.text.format_item(self.items_controller.get_by_item_id(247145)) + "\n"  # Arithmetic Lead Viralbots
            blob += "(Nanoskill / Tradeskill)\n\n"
            blob += self.text.format_item(self.items_controller.get_by_item_id(247684)) + "\n\n"  # type 1
            blob += self.text.format_item(self.items_controller.get_by_item_id(247686)) + "\n\n"  # type 2
            blob += self.text.format_item(self.items_controller.get_by_item_id(288673))  # type 48
        elif general == "Ilari":
            blob += "Low Evade/Dodge\n\n"
            blob += self.text.format_item(self.items_controller.get_by_item_id(247147)) + "\n"  # Spiritual Lead Viralbots
            blob += "(Nanocost / Nanopool / Max Nano)\n\n"
            blob += self.text.format_item(self.items_controller.get_by_item_id(247682)) + "\n\n"  # type 992
            blob += self.text.format_item(self.items_controller.get_by_item_id(247680))  # type 880
        elif general == "Rimah":
            blob += "Low Evade/Dodge\n\n"
            blob += self.text.format_item(self.items_controller.get_by_item_id(247143)) + "\n"  # Observant Lead Viralbots
            blob += "(Init / Evades)\n\n"
            blob += self.text.format_item(self.items_controller.get_by_item_id(247676)) + "\n\n"  # type 112
            blob += self.text.format_item(self.items_controller.get_by_item_id(247678))  # type 240
        elif general == "Jaax":
            blob += "High Evade, Low Dodge\n\n"
            blob += self.text.format_item(self.items_controller.get_by_item_id(247139)) + "\n"  # Strong Lead Viralbots
            blob += "(Melee / Spec Melee / Add All Def / Add Damage)\n\n"
            blob += self.text.format_item(self.items_controller.get_by_item_id(247694)) + "\n\n"  # type 3
            blob += self.text.format_item(self.items_controller.get_by_item_id(247688))  # type 4
        elif general == "Xoch":
            blob += "High Evade/Dodge, Casts Ilari Biorejuvenation heals\n\n"
            blob += self.text.format_item(self.items_controller.get_by_item_id(247137)) + "\n"  # Enduring Lead Viralbots
            blob += "(Max Health / Body Dev)\n\n"
            blob += self.text.format_item(self.items_controller.get_by_item_id(247690)) + "\n\n"  # type 5
            blob += self.text.format_item(self.items_controller.get_by_item_id(247692))  # type 12
        elif general == "Cha":
            blob += "High Evade/NR, Low Dodge\n\n"
            blob += self.text.format_item(self.items_controller.get_by_item_id(247141)) + "\n"  # Supple Lead Viralbots
            blob += "(Ranged / Spec Ranged / Add All Off)\n\n"
            blob += self.text.format_item(self.items_controller.get_by_item_id(247696)) + "\n\n"  # type 13
            blob += self.text.format_item(self.items_controller.get_by_item_id(247674))  # type 76

        return ChatBlob("General %s" % general, blob)
