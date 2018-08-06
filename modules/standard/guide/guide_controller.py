from core.decorators import instance, command
from core.chat_blob import ChatBlob
from core.command_param_types import Any
import os


@instance()
class GuideController:
    GUIDE_FILE_EXT = ".txt"

    def __init__(self):
        pass

    def inject(self, registry):
        self.text = registry.get_instance("text")

    @command(command="guides", params=[], access_level="all",
             description="Show the list of guides")
    def guide_list_cmd(self, channel, sender, reply, args):
        dir_path = self.get_base_path()
        guides = [f[:-len(self.GUIDE_FILE_EXT)] for f in os.listdir(dir_path) if f.endswith(self.GUIDE_FILE_EXT)]

        blob = ""
        for guide in guides:
            blob += self.text.make_chatcmd(guide, "/tell <myname> guides " + guide) + "\n"

        return ChatBlob("Guides (%d)" % len(guides), blob)

    @command(command="guides", params=[Any("guide")], access_level="all",
             description="Show the guide details")
    def guide_show_cmd(self, channel, sender, reply, args):
        guide = args[0].lower()
        file_path = self.get_base_path() + os.sep + guide + self.GUIDE_FILE_EXT

        try:
            with open(file_path, "r") as f:
                return ChatBlob(guide.capitalize(), f.read())
        except FileNotFoundError:
            return "Could not find guide <highlight>%s<end>." % guide

    def get_base_path(self):
        return os.path.dirname(os.path.realpath(__file__)) + os.sep + "guides"
