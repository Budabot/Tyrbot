import urllib3
import re
from bs4 import BeautifulSoup
from typing import List
from core.decorators import instance, command, setting
from core.setting_types import TextSettingType, NumberSettingType
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

    @setting(name="max_multiple_results", value=10, description="Sets the default maximum number of results processed "
                                                                "when a search string yields more than 1 result")
    def max_multiple_results(self):
        return NumberSettingType()

    @command(command="auno", params=[Any("search")], access_level="member",
             description="Fetch comments for item from Auno")
    def auno_comments_cmd(self, _, search):
        item = re.findall("<a href=\"itemref://(\d+)/(\d+)/\d+\">([^<]+)</a>", search)

        if item:
            low_id, high_id, name = item[0]
        elif self.is_int(search):
            item = self.items_controller.get_by_item_id(int(search))
            if item:
                low_id = item.lowid
                high_id = item.highid
                name = item.name
        else:
            items = self.items_controller.find_items(search)
            count = len(items)

            if count > 0:
                if count > 1:
                    link_txt = "Multiple search results for \"%s\" (%s)" % (search, count)
                    return ChatBlob(link_txt, self.multiple_results_blob(items, search))
                else:
                    high_id = items[0].highid
                    low_id = items[0].lowid
                    name = items[0].name
            else:
                return "No items found matching <highlight>%s<end>" % search

        combined_response = self.get_auno_response(low_id, high_id)

        if len(combined_response) > 0:
            # high id comments
            soup = BeautifulSoup(combined_response[0].data)
            comments: List[AunoComment] = self.find_comments(soup)

            if len(combined_response) > 1:
                # low id comments
                soup = BeautifulSoup(combined_response[1].data)
                comments += self.find_comments(soup)

            # sort the comments by date
            comments.sort(key=lambda comment: comment.date)

            if len(comments) > 0:
                return ChatBlob("Comments for %s (%s)" % (name, len(comments)),
                                self.build_comments_blob(comments, name, low_id, high_id))
            else:
                return "No comments found for <highlight>%s<end>" % name
        else:
            return "Error fetching comments from auno"

    def build_comments_blob(self, comments, name, low_id, high_id):
        link_auno = self.text.make_chatcmd("Auno", "/start %s" % self.get_auno_request_url(high_id))
        link_aoitems = self.text.make_chatcmd("AOItems", "/start %s" % self.get_aoitems_request_url(high_id))

        ql = self.items_controller.get_by_item_id(high_id).highql
        blob = "Item: %s\n" % self.text.make_item(int(low_id), int(high_id), int(ql), name)
        blob += "Item links: [%s] [%s]\n\n" % (link_auno, link_aoitems)
        blob += "<header2>Comments<end>\n"

        for comment in comments:
            blob += "<red>%s<end> [<grey>%s<end>]\n" % (comment.author, comment.date)
            blob += "%s\n\n<pagebreak>" % comment.content

        return blob

    def multiple_results_blob(self, items, search):
        max_multiple_results = int(self.setting_service.get("max_multiple_results").get_value())

        blob = "Found <highlight>%s<end> items matching <highlight>\"%s\"<end>\n" % (len(items), search)
        if len(items) > max_multiple_results:
            blob += "Results have been truncated to only show the first %s results...\n\n" % max_multiple_results
            items = items[:max_multiple_results]

        for i, item in enumerate(items):
            itemref = self.text.make_item(item.lowid, item.highid, item.highql, item.name)
            comments_link = self.text.make_chatcmd("Comments", "/tell <myname> auno %s" % item.highid)
            auno_link_h = self.text.make_chatcmd("Auno", "/start %s" % self.get_auno_request_url(item.highid))
            blob += "%s. %s\n | [%s] [%s]" % (i+1, itemref, comments_link, auno_link_h)
            blob += "\n\n<pagebreak>"

        return blob

    def find_comments(self, soup):
        comments: List[AunoComment] = []

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

    def get_auno_response(self, low_id, high_id):
        auno_request_low = self.get_auno_request_url(low_id)
        auno_request_high = self.get_auno_request_url(high_id)

        auno_http = urllib3.PoolManager()
        auno_response_h = auno_http.request('GET', auno_request_high)
        auno_response_l = None

        if low_id != high_id:
            auno_response_l = auno_http.request('GET', auno_request_low)

        combined_response = []

        if auno_response_h:
            if auno_response_h.status == 200:
                combined_response.append(auno_response_h)
        if auno_response_l:
            if auno_response_l.status == 200:
                combined_response.append(auno_response_l)

        return combined_response

    def get_auno_request_url(self, item_id):
        return "https://auno.org/ao/db.php?id=%s" % item_id

    def get_aoitems_request_url(self, item_id):
        return "https://aoitems.com/item/%s/" % item_id

    def is_int(self, s):
        try:
            int(s)
            return True
        except ValueError:
            return False
