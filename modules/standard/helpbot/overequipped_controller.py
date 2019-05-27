from core.decorators import instance, command
from core.command_param_types import Int
from core.db import DB
from core.dict_object import DictObject
from core.text import Text
from core.chat_blob import ChatBlob
import math


@instance()
class OverequippedController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.discord_controller = registry.get_instance("discord_controller")

    def start(self):
        self.discord_controller.register_discord_command_handler(self.oe_discord_cmd, "oe", [Int("skill_level")])

    @command(command="oe", params=[Int("skill_level")], access_level="all",
             description="Show the current time in every timezone")
    def oe_command(self, request, skill_level):
        oe = self.get_oe_vals(skill_level)

        blob = "With a skill requirement of <highlight>%s<end>, you will be\n" % skill_level
        blob += "Out of OE: <highlight>%d<end> or higher\n" % oe.oe100low
        blob += "75%%: <highlight>%d<end> to <highlight>%d<end>\n" % (oe.oe75low, oe.oe100low - 1)
        blob += "50%%: <highlight>%d<end> to <highlight>%d<end>\n" % (oe.oe50low, oe.oe75low - 1)
        blob += "25%%: <highlight>%d<end> to <highlight>%d<end>\n" % (oe.oe25low, oe.oe50low - 1)
        blob += "0%%: <highlight>%d<end> or lower\n\n" % (oe.oe25low - 1)

        blob += "With a personal skill of <highlight>%s<end>, you can use up to\n" % skill_level
        blob += "Out of OE: <highlight>%d<end> or lower\n" % oe.oe100
        blob += "75%%: <highlight>%d<end> to <highlight>%d<end>\n" % (oe.oe100 + 1, oe.oe75)
        blob += "50%%: <highlight>%d<end> to <highlight>%d<end>\n" % (oe.oe75 + 1, oe.oe50)
        blob += "25%%: <highlight>%d<end> to <highlight>%d<end>\n" % (oe.oe50 + 1, oe.oe25)
        blob += "0%%: <highlight>%d<end> or higher\n" % (oe.oe25 - 1)

        return ChatBlob("%d - %d - %d" % (oe.oe100low, skill_level, oe.oe100), blob)

    def get_oe_vals(self, skill_level):
        return DictObject({
            "oe100": int(math.floor(skill_level / 0.8)),
            "oe100low": int(math.floor(skill_level * 0.8)),
            "oe75": int(math.floor(skill_level / 0.6)),
            "oe75low": int(math.floor(skill_level * 0.6)),
            "oe50": int(math.floor(skill_level / 0.4)),
            "oe50low": int(math.floor(skill_level * 0.4)),
            "oe25": int(math.floor(skill_level / 0.2)),
            "oe25low": int(math.floor(skill_level * 0.2))})

    def oe_discord_cmd(self, ctx, reply, args):
        skill_level, = args
        oe = self.get_oe_vals(skill_level)

        reply("%d - %d - %d" % (oe.oe100low, skill_level, oe.oe100), "OE")
