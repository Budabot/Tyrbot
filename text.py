from decorators import instance
from setting_manager import SettingManager


@instance
class Text:
    def __init__(self):
        pass

    def inject(self, registry):
        self.setting_manager: SettingManager = registry.get_instance("settingmanager")

    def start(self):
        pass

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

    def paginate(self, name, msg, max_page_length):
        # TODO include header size in calc?
        separators = ["<pagebreak>", "\n", " "]

        msg = msg.strip()
        msg = msg.replace('"', "&quot;")
        name = name.replace('"', "&quot;")

        msg = self.format_message(msg)

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

        if len(pages) == 1:
            return [self.format_page(name, name, pages[0])]
        else:
            i = 0
            for page in pages:
                i += 1
                header = name + " (Page " + str(i) + " / " + str(len(pages)) + ")"
                yield self.format_page(name, header, page)

    def format_page(self, name, header, msg):
        return "<a href=\"text://<header>" + header + "<end>\n\n" + msg + "\">" + name + "</a>"

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
            .replace("<header>", self.setting_manager.get("header_color"))\
            .replace("<header2>", self.setting_manager.get("header2_color"))\
            .replace("<highlight>", self.setting_manager.get("highlight_color"))\
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
            .replace("<neutral>", self.setting_manager.get("neutral_color"))\
            .replace("<omni>", self.setting_manager.get("omni_color"))\
            .replace("<clan>", self.setting_manager.get("clan_color"))\
            .replace("<unknown>", self.setting_manager.get("unknown_color"))\
            \
            .replace("<myname>", "TODO")\
            .replace("<myorg>", "TODO")\
            .replace("<tab>", "    ")\
            .replace("<end>", "</font>")\
            .replace("<symbol>", self.setting_manager.get("symbol"))\
            .replace("<br>", "\n")
