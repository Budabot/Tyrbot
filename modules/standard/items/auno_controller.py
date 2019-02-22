import urllib3
import re
from bs4 import BeautifulSoup
from typing import List
from core.decorators import instance, command, setting
from core.setting_types import TextSettingType
from core.command_param_types import Int, Any, Const
from core.chat_blob import ChatBlob
from core.lookup.character_service import CharacterService
from core.tyrbot import Tyrbot
from core.db import DB
from core.setting_service import SettingService
from core.event_service import EventService
from core.text import Text
from core.command_service import CommandService
from .items_controller import ItemsController
from .auno_comment import AunoComment


@instance()
class AunoController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.db: DB = registry.get_instance("db")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.event_service: EventService = registry.get_instance("event_service")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.text: Text = registry.get_instance("text")
        self.command_service: CommandService = registry.get_instance("command_service")
        self.items_controller: ItemsController = registry.get_instance("items_controller")

    @setting(name="auno_url", value="https://auno.org/ao/db.php",
             description="Set the auno base url for looking up items in the auno db")
    def auno_url(self):
        return TextSettingType(options=["https://auno.org/ao/db.php"])

    @command(command="auno", params=[Int("ql", is_optional=True), Any("search")], access_level="member",
             description="Fetch comments for item from Auno")
    def auno_comments_cmd(self, _, ql, search):
        item = re.findall("<a href=\"itemref://(\d+)/(\d+)/(\d+)\">([^<]+)</a>", search)

        if item:
            low_id, item_id, ql, name = item[0]
        else:
            items = self.items_controller.find_items(search, ql)
            count = len(items)
            if count > 0:
                if count > 1:
                    return ChatBlob("Multiple search results for \"%s\" (%s)" % (search, count),
                                    self.multiple_results_blob(items[:10], search, ql, count))
                else:
                    ql = ql or items[0].highql
                    item_id = items[0].highid
                    low_id = items[0].lowid
                    name = items[0].name
            else:
                if ql:
                    return "No QL <highlight>%s<end> items matching <highlight>%s<end>" % (ql, search)
                else:
                    return "No items found matching <highlight>%s<end>" % search

        auno_response = self.get_auno_response(item_id, ql)

        if auno_response:
            soup = BeautifulSoup(auno_response.data)
            comments: List[AunoComment] = self.find_comments(soup)

            if len(comments) > 0:
                return ChatBlob("Comments for %s (%s)" % (name, len(comments)),
                                self.build_comments_blob(comments, name, item_id, low_id, ql))
            else:
                return "No comments found for <highlight>%s<end>" % name
        else:
            return "Error fetching comments from auno"

    @command(command="aunoid", params=[Int("ql"), Int("item_id")], access_level="member",
             description="Fetch comments for item from Auno using item id")
    def auno_comments_with_item_id_cmd(self, _1, ql, item_id):
        auno_response = self.get_auno_response(item_id, ql)

        if auno_response:
            soup = BeautifulSoup(auno_response.data)
            comments: List[AunoComment] = self.find_comments(soup)
            item = self.items_controller.get_by_item_id(item_id)

            if len(comments) > 0:
                return ChatBlob("Comments for %s (%s)" % (item.name, len(comments)),
                                self.build_comments_blob(comments, item.name, item_id, item.lowid, ql))
            if item:
                return "No comments found for <highlight>%s<end>" % item.name
            else:
                return "No item matching id <highlight>%s<end>" % item_id

    def build_comments_blob(self, comments, name, item_id, low_id, ql):
        link_auno = self.text.make_chatcmd("Auno", "/start %s" % self.get_auno_request_url(item_id, ql))
        link_aoitems = self.text.make_chatcmd("AOItems", "/start %s" % self.get_aoitems_request_url(item_id, ql))

        blob = "Item: %s\n" % self.text.make_item(int(low_id), int(item_id), int(ql), name)
        blob += "Item links: [%s] [%s]\n\n" % (link_auno, link_aoitems)
        blob += "<header2>Comments<end>\n"

        for comment in comments:
            blob += "<red>%s<end> [<grey>%s<end>]\n" % (comment.author, comment.date)
            blob += "%s\n\n<pagebreak>" % comment.content

        return blob

    def multiple_results_blob(self, items, search, ql, count):
        with_ql = " at QL <highlight>%s" % ql
        blob = "Found <highlight>%s<end> items matching <highlight>\"%s\"<end>%s\n" % (count, search, with_ql)
        if count > len(items):
            blob += "Results have been truncated to only show the first 10 results...\n\n"

        for i, item in enumerate(items):
            comments_link = self.text.make_chatcmd("comments", "/tell <myname> aunoid %s %s" %
                                                   (ql or item.highql, item.highid))
            blob += "%s. %s [%s]" % (i+1, self.text.make_item(item.lowid, item.highid, ql or item.highql, item.name),
                                     comments_link)
            blob += "\n<pagebreak>"

        return blob

    def find_comments(self, soup):
        comments = []

        brs = soup.find_all("br")
        for br in brs:
            br.replace_with("\n")

        trs = soup.find_all(self.tr_contains_comment)
        for tr in trs:
            author, date = tr.find("span").string.split("@")

            comment_content = tr.find("div")
            comment = ""

            for content in comment_content:
                if type(content) is str:
                    comment += content
                else:
                    comment += content.string

            # when those halfwits think a billion linebreaks are necessary
            # and because auno's comment output is ever so lovely...
            comment = re.sub("(\\n(?:\\n)*(?:\s)*)", "\n", comment)

            comments.append(AunoComment(author.strip(), date.strip(), comment.strip()))

        return comments

    def tr_contains_comment(self, tag):
        if tag:
            if 'id' in tag.attrs:
                p = re.compile("aoc\d+")
                return p.match(tag['id'])

    def get_auno_response(self, item_id, ql):
        auno_request = self.get_auno_request_url(item_id, ql)

        if auno_request:
            auno_http = urllib3.PoolManager()
            auno_response = auno_http.request('GET', auno_request)

            if auno_response:
                if auno_response.status == 200:
                    return auno_response

        return None

    def get_auno_request_url(self, item_id, ql):
        return "%s?id=%s&ql=%s" % (self.setting_service.get("auno_url").get_value() or
                                   "https://auno.org/ao/db.php", item_id, ql)

    def get_aoitems_request_url(self, item_id, ql):
        return "%s/%s/%s/" % (self.setting_service.get("aoitems_url") or "https://aoitems.com/item", item_id, ql)
