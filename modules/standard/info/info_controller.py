import pathlib

from core.decorators import instance, command
from core.chat_blob import ChatBlob
from core.command_param_types import Any
import os


@instance()
class InfoController:
    FILE_EXT = ".txt"
    CUSTOM_DATA_DIRECTORY = "./data/info"

    def __init__(self):
        self.paths = []
        self.paths.append(os.path.dirname(os.path.realpath(__file__)) + os.sep + "info")
        self.paths.append(self.CUSTOM_DATA_DIRECTORY)

    def inject(self, registry):
        self.text = registry.get_instance("text")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("guides", "info")
        self.command_alias_service.add_alias("breed", "info breed")
        self.command_alias_service.add_alias("healdelta", "info healdelta")
        self.command_alias_service.add_alias("nanodelta", "info nanodelta")
        self.command_alias_service.add_alias("lag", "info lag")
        self.command_alias_service.add_alias("stats", "info stats")
        self.command_alias_service.add_alias("light", "info light")
        self.command_alias_service.add_alias("doja", "info doja")

        pathlib.Path(self.CUSTOM_DATA_DIRECTORY).mkdir(parents=True, exist_ok=True)

    @command(command="info", params=[], access_level="all",
             description="Show the list of info topics")
    def info_list_cmd(self, request):
        topics = self.get_all_topics()

        blob = ""
        for topic in topics:
            blob += self.text.make_chatcmd(topic, "/tell <myname> info " + topic) + "\n"

        return ChatBlob("Info Topics (%d)" % len(topics), blob)

    @command(command="info", params=[Any("topic")], access_level="all",
             description="Show the info topic details")
    def info_show_cmd(self, request, topic_name):
        topic = self.get_topic_info(topic_name)

        if topic:
            return ChatBlob(topic_name.capitalize(), topic)
        else:
            return "Could not find info topic <highlight>%s<end>." % topic_name

    def register_path(self, path):
        self.paths.append(path)

    def get_topic_info(self, name):
        name = name.lower()
        for base in reversed(self.paths):
            file_path = base + os.sep + name + self.FILE_EXT
            try:
                with open(file_path, "r") as f:
                    return f.read()
            except FileNotFoundError:
                pass

        return None

    def get_all_topics(self):
        topics = []
        for base in reversed(self.paths):
            topics += [f[:-len(self.FILE_EXT)] for f in os.listdir(base) if f.endswith(self.FILE_EXT)]
        return sorted(set(topics))
