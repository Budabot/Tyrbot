import re
from html.parser import HTMLParser

from core.decorators import instance
from core.feature_flags import FeatureFlags
from core.logger import Logger
from core.setting_service import SettingService


class TextFormatter(HTMLParser):
    def __init__(self, bot, setting_service, public_channel_service):
        super().__init__(convert_charrefs=False)
        self.logger = Logger(__name__)
        self.strict = False
        self.fed = []
        self.stack = []
        self.single_tags = ["br", "symbol", "tab", "myorg", "myname", "pagebreak", "img"]

        self.bot = bot
        self.setting_service = setting_service
        self.public_channel_service = public_channel_service

    def reset(self):
        super().reset()
        self.fed = []
        self.stack = []

    def handle_entityref(self, name):
        # print("entityref " + name)
        self.handle_data("&" + name + ";")

    def handle_charref(self, name):
        # print("charref " + name)
        pass

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return "".join(self.fed)

    def handle_starttag(self, tag, attrs):
        if tag == "header":
            self.handle_data(self.setting_service.get("header_color").get_font_color())
        elif tag == "header2":
            self.handle_data(self.setting_service.get("header2_color").get_font_color())
        elif tag == "highlight":
            self.handle_data(self.setting_service.get("highlight_color").get_font_color())
        elif tag == "notice":
            self.handle_data(self.setting_service.get("notice_color").get_font_color())

        elif tag == "green":
            self.handle_data("<font color='#00DE42'>")
        elif tag == "red":
            self.handle_data("<font color='#FF0000'>")
        elif tag == "black":
            self.handle_data("<font color='#000000'>")
        elif tag == "white":
            self.handle_data("<font color='#FFFFFF'>")
        elif tag == "yellow":
            self.handle_data("<font color='#FFFF00'>")
        elif tag == "blue":
            self.handle_data("<font color='#8CB5FF'>")
        elif tag == "orange":
            self.handle_data("<font color='#FCA712'>")
        elif tag == "grey":
            self.handle_data("<font color='#C3C3C3'>")
        elif tag == "cyan":
            self.handle_data("<font color='#00FFFF'>")
        elif tag == "violet":
            self.handle_data("<font color='#8F00FF'>")

        elif tag == "neutral":
            self.handle_data(self.setting_service.get("neutral_color").get_font_color())
        elif tag == "omni":
            self.handle_data(self.setting_service.get("omni_color").get_font_color())
        elif tag == "clan":
            self.handle_data(self.setting_service.get("clan_color").get_font_color())
        elif tag == "unknown":
            self.handle_data(self.setting_service.get("unknown_color").get_font_color())

        elif tag == "myname":
            self.handle_data(self.bot.get_char_name())
        elif tag == "myorg":
            self.handle_data(self.public_channel_service.get_org_name() or "Unknown Org")
        elif tag == "tab":
            self.handle_data("    ")
        elif tag == "end":
            self.logger.warning("Using deprecated 'end' markup tag")
            self.handle_data("</font>")
        elif tag == "symbol":
            self.handle_data(self.setting_service.get("symbol").get_value())
        elif tag == "br":
            self.handle_data("\n")
        elif tag == "a":
            for k, v in attrs:
                if k == "href":
                    text_formatter = TextFormatter(self.bot, self.setting_service, self.public_channel_service)
                    href = text_formatter.format_message(v)
                    if href.startswith("text://"):
                        self.handle_data("<a href=\"")
                        self.handle_data(href)
                        self.handle_data("\">")
                    else:
                        self.handle_data("<a href='")
                        self.handle_data(href)
                        self.handle_data("'>")
                    break
        else:
            self.handle_data(self.get_starttag_text())

        if tag not in self.single_tags:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if self.stack and tag == self.stack[-1]:
            self.stack.pop()
            if tag == "a":
                self.handle_data("</a>")
            else:
                self.handle_data("</font>")
        else:
            self.logger.warning(f"Malformed markup for end tag '{tag}' at position '{self.getpos()}'")

    def error(self, message):
        self.logger.error(message)

    def format_message(self, message):
        self.feed(message)
        return self.get_data()


@instance()
class Text:
    separators = [{"symbol": "<pagebreak>", "include": False}, {"symbol": "\n", "include": True}, {"symbol": " ", "include": True}]

    # taken from IGN bot
    pixel_mapping = {'i': 3, 'l': 3, 'K': 10, 'R': 10, "'": 3, 'e': 8, 'U': 10, 'j': 5, 'I': 5, '|': 6, 'N': 10, 'f': 5, '.': 5, ' ': 5,
                     ',': 5, 'J': 6, 'r': 6, 't': 6, '!': 6, '(': 6, ')': 6, '[': 6, ']': 6, '/': 6, ':': 6, ';': 6, '"': 6, 'c': 7,
                     '-': 7, 's': 8, 'v': 8, 'k': 8, 'a': 8, 'y': 8, 'z': 8, 'F': 8, 'L': 8, 'P': 8, 'n': 9, '3': 9, 'b': 9, 'd': 9,
                     'g': 9, 'h': 9, 'Y': 9, 'S': 10, 'Q': 11, 'w': 11, '<': 11, '>': 11, '=': 11, 'q': 9, 'u': 9, 'x': 9, '0': 9,
                     '1': 9, '2': 9, '4': 9, '5': 9, '6': 9, '7': 9, '8': 9, '9': 9, 'E': 9, 'T': 9, '$': 9, '*': 9, '{': 9, '}': 9,
                     '_': 9, '`': 9, 'A': 10, 'B': 10, 'C': 10, 'H': 10, 'V': 10, 'X': 10, 'Z': 10, '&': 10, 'D': 11, 'G': 11, 'M': 11,
                     'O': 11, '+': 11, '~': 11, '%': 15, 'p': 9, 'm': 13, 'o': 9, '@': 14, 'W': 15}

    def __init__(self):
        self.logger = Logger(__name__)
        self.items_regex = re.compile(r"<a href=\"itemref://(\d+)/(\d+)/(\d+)\">(.+?)</a>")

    def inject(self, registry):
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.bot = registry.get_instance("bot")
        self.public_channel_service = registry.get_instance("public_channel_service")

    def make_chatcmd(self, name, msg, style=""):
        msg = msg.strip()
        msg = msg.replace("'", "&#39;")
        return "<a %s href='chatcmd://%s'>%s</a>" % (style, msg, name)

    def make_tellcmd(self, name, msg, style="", char="<myname>"):
        return self.make_chatcmd(name, f"/tell {char} {msg}", style)

    def make_charlink(self, char, style=""):
        return "<a %s href='user://%s'>%s</a>" % (style, char, char)

    def make_item(self, low_id, high_id, ql, name):
        return "<a href='itemref://%d/%d/%d'>%s</a>" % (low_id, high_id, ql, name)

    def make_image(self, image_id, image_db="rdb"):
        return "<img src='%s://%s'>" % (image_db, image_id)

    def format_item(self, item, ql=None, with_icon=True):
        if not item:
            return None

        ql = ql or item["highql"]

        result = self.make_item(item["lowid"], item["highid"], ql, item["name"])

        if with_icon:
            result = self.make_image(item["icon"]) + "\n" + result

        return result

    def generate_item(self, item, ql, synonym=None):
        if synonym:
            return {"icon_%s" % synonym: self.make_item(item.lowid, item.highid, ql, self.make_image(item.icon)),
                    "text_%s" % synonym: self.make_item(item.lowid, item.highid, ql, item.name)}
        else:
            return {"icon": self.make_item(item.lowid, item.highid, ql, self.make_image(item.icon)),
                    "text": self.make_item(item.lowid, item.highid, ql, item.name)}

    def format_char_info(self, char_info, online_status=None):
        if char_info.org_name and char_info.org_rank_name:
            msg = "<highlight>%s</highlight> (%d/<green>%d</green>) %s %s, %s of <highlight>%s</highlight>" % \
                   (char_info.name, char_info.level, char_info.ai_level, self.get_formatted_faction(char_info.faction), char_info.profession, char_info.org_rank_name, char_info.org_name)
        elif char_info.level:
            msg = "<highlight>%s</highlight> (%d/<green>%d</green>) %s %s" % \
                   (char_info.name, char_info.level, char_info.ai_level, self.get_formatted_faction(char_info.faction), char_info.profession)
        elif char_info.name:
            msg = "<highlight>%s</highlight>" % char_info.name
        else:
            msg = "<highlight>CharId(%d)</highlight>" % char_info.char_id

        if online_status is not None:
            msg += " :: " + ("<green>Online</green>" if online_status else "<red>Offline</red>")

        return msg

    def get_formatted_faction(self, faction, contents=None):
        if not contents:
            contents = faction.capitalize()
        faction = faction.lower()
        if faction == "omni":
            return f"<omni>{contents}</omni>"
        elif faction == "clan":
            return f"<clan>{contents}</clan>"
        elif faction == "neutral":
            return f"<neutral>{contents}</neutral>"
        else:
            return f"<unknown>{contents}</unknown>"

    def paginate_single(self, chatblob):
        return self.paginate(chatblob, 8000)[0]

    def paginate(self, chatblob, max_page_length=None, max_num_pages=None, footer=None):
        label = chatblob.title
        msg = chatblob.msg

        msg = msg.strip()

        # chat blobs with empty messages are rendered as simple strings instead of links
        if not msg:
            return [label]

        msg = self.items_regex.sub(r"<a href='itemref://\1/\2/\3'>\4</a>", msg)

        color = self.setting_service.get("blob_color").get_font_color()
        msg = ("<header>" + label + "</header>\n\n" + color + msg).replace("\"", "&quot;")
        msg = self.format_message(msg)

        if footer:
            footer = "\n\n" + self.format_message(footer.replace("\"", "&quot;").strip())
        else:
            footer = ""

        adjusted_max_page_length = None
        if max_page_length:
            adjusted_max_page_length = max_page_length - len(footer)
        pages = self.split_by_separators(msg, adjusted_max_page_length, max_num_pages)
        pages = list(map(lambda p: p + footer, pages))

        num_pages = len(pages)

        def mapper(tup):
            page, index = tup
            if num_pages == 1:
                label2 = self.format_message(label)
            else:
                label2 = self.format_message(label) + " (Page " + str(index) + " / " + str(num_pages) + ")"
            return chatblob.page_prefix + self.format_page(label2, page) + chatblob.page_postfix

        return list(map(mapper, zip(pages, range(1, num_pages + 1))))

    def split_by_separators(self, content, max_page_length=None, max_num_pages=None):
        separators = iter(self.separators)

        separator = next(separators)
        rest = content
        current_page = ""
        pages = []

        while len(rest) > 0:
            line, rest = self.get_next_line(rest, separator)
            line_length = len(line)

            # if separator is not sufficient, try the next one
            if max_page_length and line_length > max_page_length:
                try:
                    separator = next(separators)
                    rest = line + rest
                    continue
                except StopIteration:
                    # this is thrown when there are no more separators in the iterator
                    raise Exception("Could not paginate: page is too large")

            if max_num_pages == len(pages) + 1:
                if max_page_length and (len(current_page) + line_length > max_page_length):
                    break
            else:
                if max_page_length and len(current_page) + line_length > max_page_length:
                    pages.append(current_page.strip())
                    current_page = ""

            current_page += line

        current_page = current_page.strip()
        if max_page_length and len(current_page) > max_page_length:
            pages.append(current_page)
        else:
            pages.append(current_page)

        return pages

    def format_page(self, label, msg):
        return "<a href=\"text://%s\">%s</a>" % (msg, label)

    def get_next_line(self, msg, separator):
        result = msg.split(separator["symbol"], 1)
        line = result[0]
        if len(result) == 1:
            rest = ""
        else:
            rest = result[1:][0]

        if separator["include"]:
            line += separator["symbol"]

        return line, rest

    def pad(self, s, length, char=" "):
        if s is None:
            s = ""

        s_pixel_width = self.get_pixel_width(s)
        spacer_pixel_width = self.pixel_mapping[char]
        fill_width = length - s_pixel_width
        if fill_width > 0:
            num_spacers = round(fill_width / spacer_pixel_width)
        else:
            num_spacers = 0
        return s + (num_spacers * char)

    def get_pixel_width(self, s):
        width = 0
        for c in s:
            pixel_width = self.pixel_mapping.get(c, None)
            if not pixel_width:
                self.logger.warning(f"Unknown pixel width mapping for char '{c}'")
                pixel_width = 8
            width += pixel_width or 8
        return width

    def format_message(self, msg):
        if FeatureFlags.TEXT_FORMATTING_V2:
            return self.format_message_new(msg)
        else:
            return self.format_message_old(msg)

    def format_message_new(self, msg):
        text_formatter = TextFormatter(self.bot, self.setting_service, self.public_channel_service)
        return text_formatter.format_message(msg)

    def format_message_old(self, msg):
        for t in ["</header>", "</header2>", "</highlight>", "</notice>", "</black>", "</white>", "</yellow>", "</blue>", "</green>", "</red>", "</orange>", "</grey>", "</cyan>",
                  "</violet>", "</neutral>", "</omni>", "</clan>", "</unknown>"]:
            msg = msg.replace(t, "</font>")

        return msg \
            .replace("<header>", self.setting_service.get("header_color").get_font_color()) \
            .replace("<header2>", self.setting_service.get("header2_color").get_font_color()) \
            .replace("<highlight>", self.setting_service.get("highlight_color").get_font_color()) \
            .replace("<notice>", self.setting_service.get("notice_color").get_font_color()) \
            \
            .replace("<black>", "<font color='#000000'>") \
            .replace("<white>", "<font color='#FFFFFF'>") \
            .replace("<yellow>", "<font color='#FFFF00'>") \
            .replace("<blue>", "<font color='#8CB5FF'>") \
            .replace("<green>", "<font color='#00DE42'>") \
            .replace("<red>", "<font color='#FF0000'>") \
            .replace("<orange>", "<font color='#FCA712'>") \
            .replace("<grey>", "<font color='#C3C3C3'>") \
            .replace("<cyan>", "<font color='#00FFFF'>") \
            .replace("<violet>", "<font color='#8F00FF'>") \
            \
            .replace("<neutral>", self.setting_service.get("neutral_color").get_font_color()) \
            .replace("<omni>", self.setting_service.get("omni_color").get_font_color()) \
            .replace("<clan>", self.setting_service.get("clan_color").get_font_color()) \
            .replace("<unknown>", self.setting_service.get("unknown_color").get_font_color()) \
            \
            .replace("<myname>", self.bot.get_char_name()) \
            .replace("<myorg>", self.public_channel_service.get_org_name() or "Unknown Org") \
            .replace("<tab>", "    ") \
            .replace("<end>", "</font>") \
            .replace("<symbol>", self.setting_service.get("symbol").get_value()) \
            .replace("<br>", "\n")
