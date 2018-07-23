from core.decorators import instance, command
from core.chat_blob import ChatBlob
from core.command_param_types import Any, Const, Int
from xml.etree import ElementTree
import os
import requests


@instance()
class AOUController:
    AOU_URL = "https://www.ao-universe.com/mobile/parser.php?bot=budabot"

    def __init__(self):
        pass

    def inject(self, registry):
        self.text = registry.get_instance("text")

    @command(command="aou", params=[Int("guide_id")], access_level="all",
             description="Show an AO-Universe guide")
    def aou_show_cmd(self, channel, sender, reply, args):
        guide_id = args[0]

        r = requests.get(self.AOU_URL + "&mode=view&id=" + str(guide_id))
        xml = ElementTree.fromstring(r.content)

        if xml.findall("./error"):
            reply("Could not find AO-Universe guide with id <highlight>%d<end>." % guide_id)
            return

        guide_info = self.get_guide_info(xml)

        blob = ""
        blob += "Id: " + self.text.make_chatcmd(guide_info["id"], "/start https://www.ao-universe.com/main.php?site=knowledge&id=%s" % guide_info["id"]) + "\n"
        blob += "Updated: <highlight>%s<end>\n" % guide_info["update"]
        blob += "Profession: <highlight>%s<end>\n" % guide_info["class"]
        blob += "Faction: <highlight>%s<end>\n" % guide_info["faction"]
        blob += "Level: <highlight>%s<end>\n" % guide_info["level"]
        blob += "Author: <highlight>%s<end>\n\n" % guide_info["author"]
        blob += self.format_aou_markup(guide_info["text"])
        blob += "\n\n<highlight>Powered by<end> " + self.text.make_chatcmd("AO-Universe.com", "/start https://www.ao-universe.com")

        reply(ChatBlob(guide_info["name"], blob))

    @command(command="aou", params=[Const("all", is_optional=True), Any("search")], access_level="all",
             description="Search for an AO-Universe guides")
    def aou_search_cmd(self, channel, sender, reply, args):
        include_all_matches = True if args[0] else False
        search = args[1]

        r = requests.get(self.AOU_URL + "&mode=search&search=" + search)
        xml = ElementTree.fromstring(r.content)

        blob = ""
        count = 0
        for section in xml.iter("section"):
            category = self.get_category(section)
            found = False
            for guide in self.get_guides(section):
                if include_all_matches or self.check_matches(category + " " + guide["name"] + " " + guide["description"], search):
                    # don't show category unless we have at least one guide for it
                    if not found:
                        blob += "\n<header2>%s<end>\n" % category
                        found = True

                    count += 1
                    blob += "%s - %s\n" % (self.text.make_chatcmd(guide["name"], "/tell <myname> aou %s" % guide["id"]), guide["description"])
        blob += "\n\nProvided by %s" % self.text.make_chatcmd("AO-Universe.com", "/start https://www.ao-universe.com")

        if count == 0:
            reply("Could not find any AO-Universe guides for search <highlight>%s<end>." % search)
        else:
            reply(ChatBlob("%sAOU Guides containing '%s' (%d)" % ("All " if include_all_matches else "", search, count), blob))

    def get_guide_info(self, xml):
        content = self.get_xml_child(xml, "section/content")
        return {
            "id": self.get_xml_child(content, "id").text,
            "category": self.get_category(self.get_xml_child(xml, "section")),
            "name": self.get_xml_child(content, "name").text,
            "update": self.get_xml_child(content, "update").text,
            "class": self.get_xml_child(content, "class").text,
            "faction": self.get_xml_child(content, "faction").text,
            "level": self.get_xml_child(content, "level").text,
            "author": self.get_xml_child(content, "author").text,
            "text": self.get_xml_child(content, "text").text
        }

    def check_matches(self, haystack, needle):
        haystack = haystack.lower()
        for n in needle.split():
            if n in haystack:
                return True
        return False

    def get_base_path(self):
        return os.path.dirname(os.path.realpath(__file__)) + os.sep + "guides"

    def get_guides(self, section):
        result = []
        for guide in section.findall("./guidelist/guide"):
            result.append({"id": guide[0].text, "name": guide[1].text, "description": guide[2].text})
        return result

    def get_category(self, section):
        result = []
        for folder_names in section.findall("./folderlist/folder/name"):
            result.append(folder_names.text)
        return " - ".join(reversed(result))

    def get_xml_child(self, xml, child_tag):
        return xml.findall("./%s" % child_tag)[0]

    def format_aou_markup(self, text):
        text = text.replace("[center]", "<center>")
        text = text.replace("[/center]", "</center>")
        text = text.replace("[i]", "<i>")
        text = text.replace("[/i]", "</i>")
        text = text.replace("[b]", "<highlight>")
        text = text.replace("[/b]", "<end>")
        text = text.replace("[ts_ts]", " + ")
        text = text.replace("[ts_ts2]", " = ")
        text = text.replace("[cttd]", " | ")
        text = text.replace("[cttr]", "\n")
        text = text.replace("[br]", "\n")

        return text
