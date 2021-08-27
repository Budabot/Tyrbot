import re
import html
import time

import requests
from bs4 import BeautifulSoup
from typing import List
from core.decorators import instance, command
from core.command_param_types import Any, Int, Item
from core.chat_blob import ChatBlob
from core.text import Text
from .items_controller import ItemsController
from .auno_comment import AunoComment


@instance()
class AunoController:
    CACHE_GROUP = "auno_comments"

    def inject(self, registry):
        self.text: Text = registry.get_instance("text")
        self.items_controller: ItemsController = registry.get_instance("items_controller")
        self.cache_service = registry.get_instance("cache_service")

    @command(command="auno", params=[Int("item_id")], access_level="member",
             description="Fetch comments for item from Auno by item id")
    def auno_comments_item_id_cmd(self, _, item_id):
        item = self.items_controller.get_by_item_id(item_id)
        if item:
            low_id = item.lowid
            high_id = item.highid
            name = item.name
        else:
            low_id = item_id
            high_id = item_id
            name = item_id

        return self.get_combined_response(low_id, high_id, name)

    @command(command="auno", params=[Item("item_link")], access_level="member",
             description="Fetch comments for item from Auno by item link")
    def auno_comments_item_link_cmd(self, _, item):
        return self.get_combined_response(item.low_id, item.high_id, item.name)

    @command(command="auno", params=[Any("search")], access_level="member",
             description="Fetch comments for item from Auno by search")
    def auno_comments_cmd(self, _, search):
        items = self.items_controller.find_items(search)
        count = len(items)

        if count > 0:
            if count > 1:
                link_txt = "Multiple search results for \"%s\" (%s)" % (search, count)
                return ChatBlob(link_txt, self.multiple_results_blob(items, search))
            else:
                return self.get_combined_response(items[0].lowid, items[0].highid, items[0].name)
        else:
            return "No items found matching <highlight>%s</highlight>." % search

    def get_combined_response(self, low_id, high_id, name):
        combined_response = []

        result = self.get_auno_response(high_id)
        if result:
            combined_response.append(result)

        if low_id != high_id:
            result = self.get_auno_response(low_id)
            if result:
                combined_response.append(result)

        if len(combined_response) > 0:
            # high id comments
            soup = BeautifulSoup(combined_response[0], features="html.parser")
            comments: List[AunoComment] = self.find_comments(soup)

            if len(combined_response) > 1:
                # low id comments
                soup = BeautifulSoup(combined_response[1], features="html.parser")
                comments += self.find_comments(soup)

            # sort the comments by date
            comments.sort(key=lambda comment: comment.date)

            if len(comments) > 0:
                return ChatBlob("Comments for %s (%s)" % (name, len(comments)),
                                self.build_comments_blob(comments, name, low_id, high_id))
            else:
                return "No comments found for <highlight>%s</highlight>." % name
        else:
            return "Error fetching comments from Auno.org."

    def build_comments_blob(self, comments, name, low_id, high_id):
        link_auno = self.text.make_chatcmd("Auno", "/start %s" % self.get_auno_request_url(high_id))
        link_aoitems = self.text.make_chatcmd("AOItems", "/start %s" % self.get_aoitems_request_url(high_id))

        item = self.items_controller.get_by_item_id(high_id)
        blob = ""
        if item:
            ql = item.highql
            blob += "Item: %s\n" % self.text.make_item(int(low_id), int(high_id), int(ql), name)
        blob += "Item links: [%s] [%s]\n\n" % (link_auno, link_aoitems)
        blob += "<header2>Comments</header2>\n"

        for comment in comments:
            blob += html.unescape(comment.content) + "\n"
            blob += "<highlight>%s</highlight> [<grey>%s</grey>]\n" % (comment.author, comment.date)
            blob += "\n<pagebreak>"

        return blob

    def multiple_results_blob(self, items, search):
        max_multiple_results = 40

        blob = "Found <highlight>%s</highlight> items matching <highlight>\"%s\"</highlight>\n" % (len(items), search)
        if len(items) > max_multiple_results:
            blob += "Results have been truncated to only show the first %s results...\n\n" % max_multiple_results
            items = items[:max_multiple_results]

        for i, item in enumerate(items):
            itemref = self.text.make_item(item.lowid, item.highid, item.highql, item.name)
            comments_link = self.text.make_tellcmd("Comments", "auno %s" % item.highid)
            auno_link_h = self.text.make_chatcmd("Auno", "/start %s" % self.get_auno_request_url(item.highid))
            blob += "%s [%s] [%s]" % (itemref, comments_link, auno_link_h)
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
                    comment += html.escape(content)
                else:
                    comment += html.escape(content.string)

            # when those halfwits think a billion linebreaks are necessary
            # and because auno's comment output is ever so lovely...
            comment = re.sub(r"(\n(?:\n)*(?:\s)*)", "\n", comment)

            comments.append(AunoComment(author.strip(), date.strip(), comment.strip()))
        return comments

    def tr_contains_comment(self, tag):
        if tag:
            if 'id' in tag.attrs:
                p = re.compile(r"aoc\d+")
                return p.match(tag['id'])

    def get_auno_response(self, _id):
        t = int(time.time())
        thirty_days = 86400 * 30

        cache_obj = self.cache_service.retrieve(self.CACHE_GROUP, f"{_id}.html")
        if cache_obj and t - thirty_days < cache_obj.last_modified:
            print("using cache")
            return cache_obj.data

        url = self.get_auno_request_url(_id)
        response = requests.get(url, timeout=5)

        if response and response.status_code == 200:
            self.cache_service.store(self.CACHE_GROUP, f"{_id}.html", response.text)
            return response.text
        else:
            return None

    def get_auno_request_url(self, item_id):
        return "https://auno.org/ao/db.php?id=%s" % item_id

    def get_aoitems_request_url(self, item_id):
        return "https://aoitems.com/item/%s/" % item_id
