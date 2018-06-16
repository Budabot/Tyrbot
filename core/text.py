from core.decorators import instance
from core.setting_manager import SettingManager


@instance()
class Text:
    separators = [{"symbol": "<pagebreak>", "include": False}, {"symbol": "\n", "include": True}, {"symbol": " ", "include": True}]

    def __init__(self):
        pass

    def inject(self, registry):
        self.setting_manager: SettingManager = registry.get_instance("setting_manager")
        self.bot = registry.get_instance("bot")

    def make_chatcmd(self, name, msg, style=""):
        msg = msg.strip()
        msg = msg.replace("'", "&#39;")
        return "<a %s href='chatcmd://%s'>%s</a>" % (style, msg, name)

    def make_charlink(self, char, style=""):
        return "<a %s href='user://%s'>%s</a>" % (style, char, char)

    def make_item(self, low_id, high_id, ql, name):
        return "<a href='itemref://%d/%d/%d'>%s</a>" % (low_id, high_id, ql, name)

    def make_image(self, image_id, image_db="rdb"):
        return "<img src='%s://%s'>" % (image_db, image_id)

    def paginate(self, label, msg, max_page_length, max_num_pages=None, footer=None):
        separators = iter(self.separators)

        msg = ("<header>" + label + "<end>\n\n" + msg.strip()).replace("\"", "&quot;")
        msg = self.format_message(msg)

        if footer:
            footer = "\n\n" + self.format_message(footer.replace("\"", "&quot;"))
        else:
            footer = ""

        separator = next(separators)

        rest = msg
        current_page = ""
        pages = []

        while len(rest) > 0:
            line, rest = self.get_next_line(rest, separator)
            line_length = len(line)

            # if separator is not sufficient, try the next one
            if line_length > max_page_length:
                try:
                    separator = next(separators)
                    rest = line + rest
                    continue
                except StopIteration:
                    # this is thrown when there are no more separators in the iterator
                    raise Exception("Could not paginate: page is too large")

            if max_num_pages == len(pages) + 1:
                if len(current_page) + line_length + len(footer) > max_page_length:
                    break
            else:
                if len(current_page) + line_length > max_page_length:
                    pages.append(current_page.strip())
                    current_page = ""

            current_page += line

        current_page = current_page.strip()
        if len(current_page) + len(footer) > max_page_length:
            pages.append(current_page)
            pages.append(footer.strip())
        else:
            pages.append(current_page + footer)

        num_pages = len(pages)

        def mapper(tup):
            page, index = tup
            if num_pages == 1:
                label2 = label
            else:
                label2 = label + " (Page " + str(index) + " / " + str(num_pages) + ")"
            return self.format_page(label2, page)

        return list(map(mapper, zip(pages, range(1, num_pages + 1))))

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

    def format_message(self, msg):
        return msg\
            .replace("<header>", self.setting_manager.get("header_color").get_font_color()) \
            .replace("<header2>", self.setting_manager.get("header2_color").get_font_color()) \
            .replace("<highlight>", self.setting_manager.get("highlight_color").get_font_color()) \
            .replace("<notice>", self.setting_manager.get("notice_color").get_font_color()) \
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
            .replace("<neutral>", self.setting_manager.get("neutral_color").get_font_color()) \
            .replace("<omni>", self.setting_manager.get("omni_color").get_font_color()) \
            .replace("<clan>", self.setting_manager.get("clan_color").get_font_color()) \
            .replace("<unknown>", self.setting_manager.get("unknown_color").get_font_color()) \
            \
            .replace("<myname>", self.bot.char_name) \
            .replace("<myorg>", self.bot.org_name if self.bot.org_name else "Unknown Org") \
            .replace("<tab>", "    ") \
            .replace("<end>", "</font>") \
            .replace("<symbol>", self.setting_manager.get("symbol").get_value()) \
            .replace("<br>", "\n")
