from core.decorators import instance, command
from core.command_param_types import Int
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob
import math


@instance()
class OverequippedController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")

    @command(command="oe", params=[Int("skill_level")], access_level="all",
             description="Show the current time in every timezone")
    def oe_command(self, channel, sender, reply, args):
        skill_level = args[0]
        oe100 = int(math.floor(skill_level / 0.8))
        oe100low = int(math.floor(skill_level * 0.8))
        oe75 = int(math.floor(skill_level / 0.6))
        oe75low = int(math.floor(skill_level * 0.6))
        oe50 = int(math.floor(skill_level / 0.4))
        oe50low = int(math.floor(skill_level * 0.4))
        oe25 = int(math.floor(skill_level / 0.2))
        oe25low = int(math.floor(skill_level * 0.2))

        blob = "With a skill requirement of <highlight>%s<end>, you will be\n" % skill_level
        blob += "Out of OE: <highlight>%d<end> or higher\n" % oe100low
        blob += "75%%: <highlight>%d<end> to <highlight>%d<end>\n" % (oe75low, oe100low - 1)
        blob += "50%%: <highlight>%d<end> to <highlight>%d<end>\n" % (oe50low, oe75low - 1)
        blob += "25%%: <highlight>%d<end> to <highlight>%d<end>\n" % (oe25low, oe50low - 1)
        blob += "0%%: <highlight>%d<end> or lower\n\n" % (oe25low - 1)

        blob += "With a personal skill of <highlight>%s<end>, you can use up to\n" % skill_level
        blob += "Out of OE: <highlight>%d<end> or lower\n" % oe100
        blob += "75%%: <highlight>%d<end> to <highlight>%d<end>\n" % (oe100 + 1, oe75)
        blob += "50%%: <highlight>%d<end> to <highlight>%d<end>\n" % (oe75 + 1, oe50)
        blob += "25%%: <highlight>%d<end> to <highlight>%d<end>\n" % (oe50 + 1, oe25)
        blob += "0%%: <highlight>%d<end> or higher\n" % (oe25 - 1)

        reply(ChatBlob("%d - %d - %d" % (oe100low, skill_level, oe100), blob))
