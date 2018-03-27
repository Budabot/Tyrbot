from core.decorators import instance
from core.settings.setting_manager import SettingManager


@instance()
class Text:
    def __init__(self):
        pass

    def inject(self, registry):
        self.setting_manager: SettingManager = registry.get_instance("setting_manager")
        self.bot = registry.get_instance("budabot")

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

    def paginate(self, label, msg, max_page_length):
        separators = ["<pagebreak>", "\n", " "]

        msg = msg.strip()
        msg = msg.replace('"', "&quot;")
        label = label.replace('"', "&quot;")

        msg = "<header>" + label + "<end>\n\n" + self.format_message(msg)

        # if msg is empty, add a space so blob will appear
        if not msg:
            msg = " "

        rest = msg
        current_page = ""
        pages = []

        while len(rest) > 0:
            line, rest = self.get_next_line(rest, max_page_length, separators)
            if len(current_page) + len(line) > max_page_length:
                pages.append(current_page)
                current_page = ""

            current_page += line

        pages.append(current_page)

        num_pages = len(pages)

        def mapper(tup):
            page, index = tup
            if num_pages == 1:
                label2 = label
            else:
                label2 = label + " (Page " + str(index) + " / " + str(num_pages) + ")"
            return self.format_page(label2, page)

        return map(mapper, zip(pages, range(1, num_pages + 1)))

    def format_page(self, label, msg):
        return "<a href=\"text://" + msg + "\">" + label + "</a>"

    def get_next_line(self, msg, max_page_length, separators):
        if len(separators) == 0:
            raise Exception("Could not paginate")

        separator = separators[0]
        result = msg.split(separator, 1)
        line = result[0]
        if len(result) == 1:
            rest = ""
        else:
            rest = result[1:][0]

        if separator == " " or separator == "\n":
            line += separator

        if len(line) > max_page_length:
            return self.get_next_line(msg, max_page_length, separators[1:])
        else:
            return line, rest

    def format_message(self, msg):
        return msg\
            .replace("<header>", "<font color='%s'>" % self.setting_manager.get("header_color").get_value())\
            .replace("<header2>", "<font color='%s'>" % self.setting_manager.get("header2_color").get_value())\
            .replace("<highlight>", "<font color='%s'>" % self.setting_manager.get("highlight_color").get_value())\
            \
            .replace("<black>", "<font color='#000000'>") \
            .replace("<white>", "<font color='#FFFFFF'>")\
            .replace("<yellow>", "<font color='#FFFF00'>")\
            .replace("<blue>", "<font color='#8CB5FF'>")\
            .replace("<green>", "<font color='#00DE42'>")\
            .replace("<red>", "<font color='#FF0000'>")\
            .replace("<orange>", "<font color='#FCA712'>")\
            .replace("<grey>", "<font color='#C3C3C3'>")\
            .replace("<cyan>", "<font color='#00FFFF'>")\
            .replace("<violet>", "<font color='#8F00FF'>")\
            \
            .replace("<neutral>", "<font color='%s'>" % self.setting_manager.get("neutral_color").get_value())\
            .replace("<omni>", "<font color='%s'>" % self.setting_manager.get("omni_color").get_value())\
            .replace("<clan>", "<font color='%s'>" % self.setting_manager.get("clan_color").get_value())\
            .replace("<unknown>", "<font color='%s'>" % self.setting_manager.get("unknown_color").get_value())\
            \
            .replace("<myname>", self.bot.char_name)\
            .replace("<myorg>", "TODO")\
            .replace("<tab>", "    ")\
            .replace("<end>", "</font>")\
            .replace("<symbol>", self.setting_manager.get("symbol").get_value())\
            .replace("<br>", "\n")
