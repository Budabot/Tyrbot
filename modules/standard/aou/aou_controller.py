import re
import time
from xml.etree import ElementTree

import bbcode
import requests

from core.chat_blob import ChatBlob
from core.command_param_types import Any, Const, Int
from core.decorators import instance, command
from core.dict_object import DictObject


@instance()
class AOUController:
    AOU_URL = "https://www.ao-universe.com/mobile/parser.php?bot=tyrbot"

    CACHE_GROUP = "aou"
    CACHE_MAX_AGE = 604800

    def __init__(self):
        self.guide_id_regex = re.compile(r"pid=(\d+)", re.IGNORECASE)

        # initialize bbcode parser
        self.parser = bbcode.Parser(install_defaults=False, newline="\n", replace_links=False, replace_cosmetic=False,
                                    drop_unrecognized=True)
        self.parser.add_simple_formatter("i", "<i>%(value)s</i>")
        self.parser.add_simple_formatter("b", "<highlight>%(value)s</highlight>")
        self.parser.add_simple_formatter("ts_ts", " + ", standalone=True)
        self.parser.add_simple_formatter("ts_ts2", " = ", standalone=True)
        self.parser.add_simple_formatter("ct", " | ", standalone=True)
        self.parser.add_simple_formatter("cttd", " | ", standalone=True)
        self.parser.add_simple_formatter("cttr", "\n | ", standalone=True)
        self.parser.add_simple_formatter("br", "\n", standalone=True)
        self.parser.add_formatter("img", self.bbcode_render_image)
        self.parser.add_formatter("url", self.bbcode_render_url)
        self.parser.add_formatter("item", self.bbcode_render_item)
        self.parser.add_formatter("itemname", self.bbcode_render_item)
        self.parser.add_formatter("itemicon", self.bbcode_render_item)
        self.parser.add_formatter("waypoint", self.bbcode_render_waypoint)

    def inject(self, registry):
        self.text = registry.get_instance("text")
        self.items_controller = registry.get_instance("items_controller")
        self.cache_service = registry.get_instance("cache_service")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("title", "aou 11")
        self.command_alias_service.add_alias("totw", "macro aou 171|aou 172")
        self.command_alias_service.add_alias("som", "macro aou 169|aou 383")
        self.command_alias_service.add_alias("reck", "aou 629")
        self.command_alias_service.add_alias("pets", "aou 2")

    @command(command="aou", params=[Int("guide_id")], access_level="all",
             description="Show an AO-Universe guide")
    def aou_show_cmd(self, request, guide_id):
        guide_info = self.retrieve_guide(guide_id)

        if not guide_info:
            return f"Could not find AO-Universe guide with id <highlight>{guide_id}</highlight>."

        guide_link = self.text.make_chatcmd(guide_info.id, "/start https://www.ao-universe.com/main.php?site=knowledge&id=%s" % guide_info.id)
        guide_link_raw = self.text.make_chatcmd("Raw", "/start %s" % (self.AOU_URL + "&mode=view&id=" + str(guide_info.id)))
        author = self.format_bbcode_code(guide_info.author)
        aou_link = self.text.make_chatcmd("AO-Universe.com", "/start https://www.ao-universe.com")

        blob = f"ID: {guide_link} ({guide_link_raw})\n"
        blob += f"Updated: <highlight>{guide_info.updated}</highlight>\n"
        blob += f"Profession: <highlight>{guide_info.profession}</highlight>\n"
        blob += f"Faction: <highlight>{guide_info.faction}</highlight>\n"
        blob += f"Level: <highlight>{guide_info.level}</highlight>\n"
        blob += f"Author: <highlight>{author}</highlight>\n\n"
        blob += self.format_bbcode_code(guide_info.text) + "\n\n"
        blob += f"\n<highlight>Powered by</highlight> {aou_link}"

        return ChatBlob(guide_info.name, blob)

    @command(command="aou", params=[Const("all", is_optional=True), Any("search")], access_level="all",
             description="Search for an AO-Universe guides")
    def aou_search_cmd(self, request, include_all_matches, search):
        include_all_matches = include_all_matches or False

        # automatically expand search if no results are found initially
        results = self.search_for_guides(search, include_all_matches)
        if not include_all_matches and len(results) == 0:
            include_all_matches = True
            results = self.search_for_guides(search, include_all_matches)

        blob = ""
        count = len(results)
        current_category = ""
        for guide in results:
            if guide["category"] != current_category:
                blob += "\n<header2>%s</header2>\n" % guide["category"]
                current_category = guide["category"]

            blob += "%s - %s\n" % (self.text.make_tellcmd(guide["name"], "aou %s" % guide["id"]), guide["description"])

        blob += "\n\nPowered by %s" % self.text.make_chatcmd("AO-Universe.com", "/start https://www.ao-universe.com")

        if count == 0:
            return f"Could not find any AO-Universe guides for search <highlight>{search}</highlight>."
        else:
            if include_all_matches:
                return ChatBlob(f"All AOU Guides containing '{search}' ({count})", blob)
            else:
                return ChatBlob(f"AOU Guides containing '{search}' ({count})", blob)

    def retrieve_guide(self, guide_id):
        cache_key = "%d.xml" % guide_id

        t = int(time.time())

        # check cache for fresh value
        cache_result = self.cache_service.retrieve(self.CACHE_GROUP, cache_key)

        if cache_result and cache_result.last_modified > (t - self.CACHE_MAX_AGE):
            result = ElementTree.fromstring(cache_result.data)
        else:
            response = requests.get(self.AOU_URL + "&mode=view&id=" + str(guide_id), timeout=5)
            result = ElementTree.fromstring(response.content)

            if result.findall("./error"):
                result = None

            if result:
                # store result in cache
                self.cache_service.store(self.CACHE_GROUP, cache_key, ElementTree.tostring(result, encoding="unicode"))
            elif cache_result:
                # check cache for any value, even expired
                result = ElementTree.fromstring(cache_result.data)

        if result:
            return self.get_guide_info(result)
        else:
            return None

    def get_guide_info(self, xml):
        content = self.get_xml_child(xml, "section/content")
        return DictObject({
            "id": self.get_xml_child(content, "id").text,
            "category": self.get_category(self.get_xml_child(xml, "section")),
            "name": self.get_xml_child(content, "name").text,
            "updated": self.get_xml_child(content, "update").text,
            "profession": self.get_xml_child(content, "class").text,
            "faction": self.get_xml_child(content, "faction").text,
            "level": self.get_xml_child(content, "level").text,
            "author": self.get_xml_child(content, "author").text,
            "text": self.get_xml_child(content, "text").text
        })

    def check_matches(self, haystack, needle):
        haystack = haystack.lower()
        for n in needle.split():
            if n in haystack:
                return True
        return False

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

    def format_bbcode_code(self, bbcode_str):
        return self.parser.format(bbcode_str or "")

    # BBCode formatters
    def bbcode_render_image(self, tag_name, value, options, parent, context):
        return self.text.make_chatcmd("Image", "/start https://www.ao-universe.com/" + value)

    def bbcode_render_url(self, tag_name, value, options, parent, context):
        url = options.get("url") or value
        guide_id_match = self.guide_id_regex.search(url)
        if guide_id_match:
            return self.text.make_tellcmd(value, "aou " + guide_id_match.group(1))
        else:
            return self.text.make_chatcmd(value, "/start " + url)

    def bbcode_render_item(self, tag_name, value, options, parent, context):
        item = self.items_controller.get_by_item_id(value)
        if not item:
            return "Unknown Item(%s)" % value
        else:
            include_icon = tag_name == "item" or tag_name == "itemicon"
            return self.text.format_item(item, with_icon=include_icon)

    def bbcode_render_waypoint(self, tag_name, value, options, parent, context):
        x_coord = options["x"]
        y_coord = options["y"]
        pf_id = options["pf"]

        return self.text.make_chatcmd("%s (%sx%s)" % (value, x_coord, y_coord), "/waypoint %s %s %s" % (x_coord, y_coord, pf_id))

    def search_for_guides(self, search, include_all_matches):
        r = requests.get(self.AOU_URL + "&mode=search&search=" + search, timeout=5)
        xml = ElementTree.fromstring(r.content)

        results = []
        for section in xml.iter("section"):
            category = self.get_category(section)
            for guide in self.get_guides(section):
                if include_all_matches or self.check_matches(category + " " + guide["name"] + " " + (guide["description"] or ""), search):
                    guide["category"] = category
                    results.append(guide)

        return results
