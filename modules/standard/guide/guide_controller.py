import pathlib

from core.decorators import instance, command
from core.chat_blob import ChatBlob
from core.command_param_types import Any
import os


@instance()
class GuideController:
    GUIDE_FILE_EXT = ".txt"
    GUIDE_DATA_DIRECTORY = "./data/guides"

    def __init__(self):
        self.guide_paths = []
        self.guide_paths.append(os.path.dirname(os.path.realpath(__file__)) + os.sep + "guides")
        self.guide_paths.append(self.GUIDE_DATA_DIRECTORY)

    def inject(self, registry):
        self.text = registry.get_instance("text")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("breed", "guides breed")
        self.command_alias_service.add_alias("healdelta", "guides healdelta")
        self.command_alias_service.add_alias("nanodelta", "guides nanodelta")
        self.command_alias_service.add_alias("lag", "guides lag")
        self.command_alias_service.add_alias("light", "guides light")
        self.command_alias_service.add_alias("stats", "guides stats")
        self.command_alias_service.add_alias("light", "guides light")

        pathlib.Path(self.GUIDE_DATA_DIRECTORY).mkdir(parents=True, exist_ok=True)

    @command(command="guides", params=[], access_level="all",
             description="Show the list of guides")
    def guide_list_cmd(self, request):
        guides = self.get_all_guides()

        blob = ""
        for guide in guides:
            blob += self.text.make_chatcmd(guide, "/tell <myname> guides " + guide) + "\n"

        return ChatBlob("Guides (%d)" % len(guides), blob)

    @command(command="guides", params=[Any("guide")], access_level="all",
             description="Show the guide details")
    def guide_show_cmd(self, request, guide_name):
        guide = self.get_guide(guide_name)

        if guide:
            return ChatBlob(guide_name.capitalize(), guide)
        else:
            return "Could not find guide <highlight>%s<end>." % guide_name

    def register_guide_path(self, path):
        self.guide_paths.append(path)

    def get_base_path(self):
        return os.path.dirname(os.path.realpath(__file__)) + os.sep + "guides"

    def get_guide(self, name):
        name = name.lower()
        for base in reversed(self.guide_paths):
            file_path = base + os.sep + name + self.GUIDE_FILE_EXT
            try:
                with open(file_path, "r") as f:
                    return f.read()
            except FileNotFoundError:
                pass

        return None

    def get_all_guides(self):
        guides = []
        for base in reversed(self.guide_paths):
            guides += [f[:-len(self.GUIDE_FILE_EXT)] for f in os.listdir(base) if f.endswith(self.GUIDE_FILE_EXT)]
        return sorted(set(guides))
