from core.alts.alts_service import AltsService
from core.decorators import instance, command, setting, event
from core.command_param_types import Const
from core.setting_types import NumberSettingType
from core.setting_service import SettingService
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob
from core.util import Util
from core.logger import Logger
from core.command_param_types import Int, Any
from core.private_channel_service import PrivateChannelService
from modules.core.org_members.org_member_controller import OrgMemberController
import time


@instance()
class NewsController:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.util: Util = registry.get_instance("util")
        self.alts_service = registry.get_instance("alts_service")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS news (id INT PRIMARY KEY AUTO_INCREMENT, char_id INT NOT NULL, news TEXT, sticky SMALLINT NOT NULL, created_at INT NOT NULL, deleted_at INT NOT NULL)")
        self.db.exec("CREATE TABLE IF NOT EXISTS news_read (char_id INTEGER NOT NULL, news_id INTEGER NOT NULL)")

    @setting(name="number_news_shown", value="10", description="Maximum number of news items shown")
    def number_news_shown(self):
        return NumberSettingType()

    @command(command="news", params=[], description="Show list of news", access_level="member")
    def news_cmd(self, request):
        row = self.db.query_single("SELECT created_at FROM news WHERE deleted_at = 0 ORDER BY created_at DESC LIMIT 1")
        if row:
            t = int(time.time())
            last_updated = self.util.time_to_readable(t - row.created_at)
            return ChatBlob("News [Last updated %s ago]" % last_updated, self.format_news_entries(self.get_news()))
        else:
            return "No news."
    
    @command(command="news", params=[Const("add"), Any("news")], description="Add news entry", access_level="moderator", sub_command="update")
    def news_add_cmd(self, request, _, news):
        sql = "INSERT INTO news (char_id, news, sticky, created_at, deleted_at) VALUES (?,?,?,?,?)"
        success = self.db.exec(sql, [request.sender.char_id, news, 0, int(time.time()), 0])

        if success > 0:
            return "Successfully added news entry with ID <highlight>%d<end>." % self.db.last_insert_id()
        else:
            return "Failed to add news entry."

    @command(command="news", params=[Const("rem"), Int("news_id")], description="Remove a news entry", access_level="moderator", sub_command="update")
    def news_rem_cmd(self, request, _, news_id):
        sql = "UPDATE news SET deleted_at = ? WHERE id = ? AND deleted_at = 0"
        success = self.db.exec(sql, [int(time.time()), news_id])

        if success > 0:
            return "Successfully deleted news entry with ID <highlight>%d<end>." % news_id
        else:
            return "Could not find news entry with ID <highlight>%d<end>." % news_id

    @command(command="news", params=[Const("sticky"), Int("news_id")], description="Sticky a news entry", access_level="moderator", sub_command="update")
    def news_sticky_cmd(self, request, _, news_id):
        sql = "UPDATE news SET sticky = 1 WHERE id = ? AND deleted_at = 0"
        success = self.db.exec(sql, [news_id])

        if success > 0:
            return "Successfully updated news entry with ID <highlight>%d<end> to a sticky." % news_id
        else:
            return "Could not find news entry with ID <highlight>%d<end>." % news_id

    @command(command="news", params=[Const("unsticky"), Int("news_id")], description="Unsticky a news entry", access_level="moderator", sub_command="update")
    def news_unsticky_cmd(self, request, _, news_id):
        sql = "UPDATE news SET sticky = 0 WHERE id = ?"
        success = self.db.exec(sql, [news_id])

        if success > 0:
            return "Successfully removed news entry with ID <highlight>%d<end> as a sticky." % news_id
        else:
            return "Could not find news entry with ID <highlight>%d<end>." % news_id

    @command(command="news", params=[Const("markasread"), Int("news_id")], description="Mark a news entry as read", access_level="member")
    def news_markasread_cmd(self, request, _, news_id):
        if not self.get_news_entry(news_id):
            return "Could not find news entry with ID <highlight>%d<end>." % news_id

        sql = "INSERT INTO news_read (char_id, news_id) VALUES (?,?)"
        self.db.exec(sql, [request.sender.char_id, news_id])

        return "Successfully marked news entry with ID <highlight>%d<end> as read." % news_id

    @command(command="news", params=[Const("markasread"), Const("all")], description="Mark all news entries as read", access_level="member")
    def news_markasread_all_cmd(self, request, _1, _2):
        sql = "INSERT INTO news_read (char_id, news_id) SELECT ?, n.id FROM news n WHERE n.id NOT IN ( " \
              "SELECT r.news_id FROM news_read r WHERE char_id = ? ) AND n.deleted_at = 0 "

        main = self.alts_service.get_main(request.sender.char_id)

        num_rows = self.db.exec(sql, [request.sender.char_id, main.char_id])

        return "Successfully marked <highlight>%d<end> news entries as read." % num_rows
    
    @event(event_type=OrgMemberController.ORG_MEMBER_LOGON_EVENT, description="Send news list when org member logs on")
    def orgmember_logon_event(self, event_type, event_data):
        if not self.bot.is_ready():
            return

        main = self.alts_service.get_main(event_data.char_id)
        unread_news = self.get_unread_news(main.char_id)

        if unread_news:
            msg = self.format_unread_news(unread_news)
            self.bot.send_private_message(event_data.char_id, msg)

    @event(event_type=PrivateChannelService.JOINED_PRIVATE_CHANNEL_EVENT, description="Send news list when someone joins private channel")
    def priv_logon_event(self, event_type, event_data):
        main = self.alts_service.get_main(event_data.char_id)
        unread_news = self.get_unread_news(main.char_id)

        if unread_news:
            msg = self.format_unread_news(unread_news)
            self.bot.send_private_message(event_data.char_id, msg)

    @event(event_type=AltsService.MAIN_CHANGED_EVENT_TYPE, description="Update news items marked as read when main is changed", is_hidden=True)
    def main_changed_event(self, event_type, event_data):
        self.db.exec("UPDATE news_read SET char_id = ? WHERE char_id = ?", [event_data.new_main_id, event_data.old_main_id])

    def get_unread_news(self, char_id):
        number_news_shown = self.setting_service.get("number_news_shown").get_value()
        sql = "SELECT n.*, p.name AS author " \
              "FROM news n " \
              "LEFT JOIN alts a ON n.char_id = a.char_id " \
              "LEFT JOIN alts a2 ON (a.group_id = a2.group_id AND a2.status = ?) " \
              "LEFT JOIN player p ON p.char_id = COALESCE(a2.char_id, n.char_id) " \
              "WHERE n.id NOT IN ( SELECT r.news_id FROM news_read r WHERE char_id = ? ) " \
              "AND n.deleted_at = 0 ORDER BY n.created_at ASC LIMIT ?"
        return self.db.query(sql, [AltsService.MAIN, char_id, number_news_shown])

    def get_news(self):
        number_news_shown = self.setting_service.get("number_news_shown").get_value()
        sql = "SELECT n.*, p.name AS author " \
              "FROM news n " \
              "LEFT JOIN alts a ON n.char_id = a.char_id " \
              "LEFT JOIN alts a2 ON (a.group_id = a2.group_id AND a2.status = ?) " \
              "LEFT JOIN player p ON p.char_id = COALESCE(a2.char_id, n.char_id) " \
              "WHERE n.deleted_at = 0 ORDER BY n.sticky DESC, n.created_at DESC LIMIT ?"
        return self.db.query(sql, [AltsService.MAIN, number_news_shown])

    def format_news_entries(self, entries):
        blob = ""
        is_sticky = False
        for item in entries:
            if is_sticky != item.sticky:
                if not is_sticky:
                    blob += "<header2>Stickies<end>\n"
                elif is_sticky:
                    blob += "____________________________\n\n"

                is_sticky = item.sticky

            # remove_link = self.text.make_chatcmd("Remove", "/tell <myname> news rem %s" % item.id)
            # sticky_link = self.text.make_chatcmd("Sticky", "/tell <myname> news sticky %s" % item.id)
            timestamp = self.util.format_datetime(item.created_at)

            blob += item.news + "\n"
            blob += "- <highlight>%s<end> [%s] ID %d\n\n" % (item.author, timestamp, item.id)

        return blob

    def format_unread_news(self, entries):
        if len(entries) == 1:
            item = entries[0]
            read_link = self.text.make_chatcmd("Hide", "/tell <myname> news markasread %s" % item.id)
            read_link_blob = self.text.paginate_single(ChatBlob("Hide", "Click here to hide this news entry: " + read_link))

            timestamp = self.util.format_datetime(item.created_at)

            msg = "Unread News: "
            msg += item.news + "\n"
            msg += "- <highlight>%s<end> [%s] ID %d %s" % (item.author, timestamp, item.id, read_link_blob)
        else:
            blob = "%s\n\n" % self.text.make_chatcmd("Hide all", "/tell <myname> news markasread all")

            for item in entries:
                read_link = self.text.make_chatcmd("Hide", "/tell <myname> news markasread %s" % item.id)
                timestamp = self.util.format_datetime(item.created_at)

                blob += item.news + "\n"
                blob += "- <highlight>%s<end> [%s] ID %d %s\n\n" % (item.author, timestamp, item.id, read_link)

            msg = ChatBlob("Unread News (%d)" % len(entries), blob)

        return msg

    def get_news_entry(self, news_id):
        return self.db.query_single("SELECT * FROM news WHERE id = ?", [news_id])
