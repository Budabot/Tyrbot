from core.command_param_types import Any
from core.conn import Conn
from core.db import DB
from core.decorators import instance, command, event
from core.alts_service import AltsService
from core.chat_blob import ChatBlob
from core.private_channel_service import PrivateChannelService
from core.public_channel_service import PublicChannelService
import time
import re

from modules.core.org_members.org_member_controller import OrgMemberController


@instance()
class OnlineController:
    ORG_CHANNEL = "Org"
    PRIVATE_CHANNEL = "Private"

    def __init__(self):
        self.afk_regex = re.compile("^(afk|brb) ?(.*)$", re.IGNORECASE)
        self.channels = [(self.ORG_CHANNEL, 0), (self.PRIVATE_CHANNEL, 1)]

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db: DB = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.pork_service = registry.get_instance("pork_service")
        self.character_service = registry.get_instance("character_service")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.alts_service = registry.get_instance("alts_service")
        self.alts_controller = registry.get_instance("alts_controller")

    def start(self):
        self.db.exec("DROP TABLE IF EXISTS online")
        self.db.exec("CREATE TABLE online (char_id INT NOT NULL, afk_dt INT NOT NULL, afk_reason VARCHAR(255) DEFAULT '', channel CHAR(50) NOT NULL, dt INT NOT NULL, UNIQUE(char_id, channel))")
        self.db.exec("DELETE FROM online")

        self.command_alias_service.add_alias("o", "online")

    @command(command="online", params=[], access_level="member",
             description="Show the list of online characters")
    def online_cmd(self, request):
        return self.get_online_output()

    @command(command="online", params=[Any("profession")], access_level="member",
             description="Show the list of online characters with alts of a certain profession")
    def online_profession_cmd(self, request, prof):
        profession = self.util.get_profession(prof)
        if not profession:
            return "Error! Unknown profession <highlight>%s</highlight>." % prof

        return self.get_online_alts_output(profession)

    @command(command="count", params=[], access_level="member",
             description="Show counts of players by title level, profession, and organization")
    def count_cmd(self, request):
        data = self.db.query("SELECT p.*, o.channel, COALESCE(p.name, o.char_id) AS name FROM online o LEFT JOIN player p ON o.char_id = p.char_id ORDER BY channel ASC")

        title_levels = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
        profs = {"Adventurer": 0, "Agent": 0, "Bureaucrat": 0, "Doctor": 0, "Enforcer": 0, "Engineer": 0, "Fixer": 0, "Keeper": 0,
                 "Martial Artist": 0, "Meta-Physicist": 0, "Nano-Technician": 0, "Soldier": 0, "Trader": 0, "Shade": 0, "Unknown": 0}
        orgs = {}

        # populate counts
        for row in data:
            prof_name = row.profession if row.profession else "Unknown"
            profs[prof_name] += 1

            title_levels[self.util.get_title_level(row.level)] += 1

            org_name = row.org_name if row.org_name else "&lt;None&gt;"
            org_count = orgs.get(org_name, 0)
            orgs[org_name] = org_count + 1

        blob = ""
        blob += "<header>Title Levels</header>\n"
        for title_level, count in title_levels.items():
            if count > 0:
                blob += "%d: %d\n" % (title_level, count)

        blob += "\n\n<header>Professions</header>\n"
        for prof, count in profs.items():
            if count > 0:
                blob += "%s: %d\n" % (prof, count)

        blob += "\n\n<header>Organizations</header>\n"
        for org, count in orgs.items():
            if count > 0:
                blob += "%s: %d\n" % (org, count)

        return ChatBlob("Count (%d)" % len(data), blob)

    def get_online_characters(self, channel):
        sql = "SELECT " \
                "p1.*, " \
                "o.afk_dt, " \
                "o.afk_reason, " \
                "COALESCE(p2.name, p1.name, o.char_id) AS main, " \
                "COALESCE(p1.name, o.char_id) AS name " \
              "FROM online o " \
              "LEFT JOIN alts a1 ON o.char_id = a1.char_id " \
              "LEFT JOIN player p1 ON o.char_id = p1.char_id " \
              "LEFT JOIN alts a2 ON a1.group_id = a2.group_id AND a2.status = ? " \
              "LEFT JOIN player p2 ON a2.char_id = p2.char_id " \
              "WHERE channel = ? " \
              "ORDER BY COALESCE(p2.name, p1.name, o.char_id) ASC, COALESCE(p1.name, o.char_id) ASC"

        return self.db.query(sql, [AltsService.MAIN, channel])

    @event(PrivateChannelService.JOINED_PRIVATE_CHANNEL_EVENT, "Record in database when someone joins private channel", is_hidden=True)
    def private_channel_joined_event(self, event_type, event_data):
        self.pork_service.load_character_info(event_data.char_id)
        self.db.exec("INSERT INTO online (char_id, afk_dt, afk_reason, channel, dt) VALUES (?, ?, ?, ?, ?)",
                     [event_data.char_id, 0, "", self.PRIVATE_CHANNEL, int(time.time())])

    @event(PrivateChannelService.LEFT_PRIVATE_CHANNEL_EVENT, "Record in database when someone leaves private channel", is_hidden=True)
    def private_channel_left_event(self, event_type, event_data):
        self.db.exec("DELETE FROM online WHERE char_id = ? AND channel = ?",
                     [event_data.char_id, self.PRIVATE_CHANNEL])

    @event(OrgMemberController.ORG_MEMBER_LOGON_EVENT, "Record in database when org member logs on", is_hidden=True)
    def org_member_logon_record_event(self, event_type, event_data):
        self.pork_service.load_character_info(event_data.char_id)
        self.db.exec("INSERT INTO online (char_id, afk_dt, afk_reason, channel, dt) VALUES (?, ?, ?, ?, ?)",
                     [event_data.char_id, 0, "", self.ORG_CHANNEL, int(time.time())])

    @event(OrgMemberController.ORG_MEMBER_LOGOFF_EVENT, "Record in database when org member logs off", is_hidden=True)
    def org_member_logoff_record_event(self, event_type, event_data):
        self.db.exec("DELETE FROM online WHERE char_id = ? AND channel = ?",
                     [event_data.char_id, self.ORG_CHANNEL])

    @event(PrivateChannelService.PRIVATE_CHANNEL_MESSAGE_EVENT, "Check for afk messages in private channel")
    def afk_check_private_channel_event(self, event_type, event_data):
        if not self.bot.get_conn_by_char_id(event_data.char_id):
            self.afk_check(event_data.char_id, event_data.message, lambda msg: self.bot.send_private_channel_message(msg, conn=event_data.conn))

    @event(PublicChannelService.ORG_CHANNEL_MESSAGE_EVENT, "Check for afk messages in org channel")
    def afk_check_org_channel_event(self, event_type, event_data):
        if not self.bot.get_conn_by_char_id(event_data.char_id):
            self.afk_check(event_data.char_id, event_data.message, lambda msg: self.bot.send_org_message(msg, conn=event_data.conn))

    @event(OrgMemberController.ORG_MEMBER_LOGON_EVENT, "Send online list to org members logging in")
    def org_member_send_logon_event(self, event_type, event_data):
        if self.bot.is_ready():
            self.bot.send_private_message(event_data.char_id, self.get_online_output(), conn=event_data.conn)

    @event(PrivateChannelService.JOINED_PRIVATE_CHANNEL_EVENT, "Send online list to characters joining the private channel")
    def private_channel_send_logon_event(self, event_type, event_data):
        self.bot.send_private_message(event_data.char_id, self.get_online_output(), conn=event_data.conn)

    def afk_check(self, char_id, message, channel_reply):
        matches = self.afk_regex.search(message)
        if matches:
            char_name = self.character_service.resolve_char_to_name(char_id)
            self.set_afk(char_id, int(time.time()), message)
            # channel_reply("<highlight>%s</highlight> is now afk." % char_name)
        else:
            row = self.db.query_single("SELECT * FROM online WHERE char_id = ? AND afk_dt > 0", [char_id])
            if row:
                self.set_afk(char_id, 0, "")
                char_name = self.character_service.resolve_char_to_name(char_id)
                time_string = self.util.time_to_readable(int(time.time()) - row.afk_dt)
                channel_reply("<highlight>%s</highlight> is back after %s." % (char_name, time_string))

    def set_afk(self, char_id, dt, reason):
        self.db.exec("UPDATE online SET afk_dt = ?, afk_reason = ? WHERE char_id = ?", [dt, reason, char_id])

    def get_online_output(self):
        blob = ""
        count = 0
        for channel, _ in self.channels:
            online_list = self.get_online_characters(channel)
            if len(online_list) == 0:
                continue

            blob += "<header2>%s Channel</header2>\n" % channel

            current_main = ""
            for row in online_list:
                if current_main != row.main:
                    count += 1
                    blob += "\n%s\n" % self.text.make_tellcmd(row.main, "alts %s" % row.main)
                    current_main = row.main

                afk = ""
                if row.afk_dt > 0:
                    afk = " - <highlight>%s (%s ago)</highlight>" % (row.afk_reason, self.util.time_to_readable(int(time.time()) - row.afk_dt))

                org_info = ""
                if channel == self.PRIVATE_CHANNEL:
                    if row.org_name:
                        org_info = ", %s of %s" % (row.org_rank_name, row.org_name)

                blob += " | %s (%d/<green>%d</green>) %s %s%s%s\n" % (row.name, row.level or 0, row.ai_level or 0, row.faction, row.profession, afk, org_info)
            blob += "\n\n"

        return ChatBlob("Online (%d)" % count, blob)

    def get_char_info_display(self, char_id, conn: Conn):
        char_info = self.pork_service.get_character_info(char_id)
        if char_info:
            name = self.text.format_char_info(char_info)
        else:
            char_name = self.character_service.resolve_char_to_name(char_id)
            name = "<highlight>%s</highlight>" % char_name

        alts = self.alts_service.get_alts(char_id)
        cnt = len(alts)
        if cnt > 1:
            if alts[0].char_id == char_id:
                main = "Alts (%d)" % cnt
            else:
                main = "Alts of %s (%d)" % (alts[0].name, cnt)

            name += " - " + self.text.paginate_single(ChatBlob(main, self.alts_controller.format_alt_list(alts)), conn)

        return name

    def get_online_alts_output(self, profession):
        blob = ""
        count = 0
        for channel, _ in self.channels:
            online_list = self.get_online_alts(channel, profession)
            if len(online_list) > 0:
                blob += "<header2>%s Channel</header2>\n" % channel

            current_main = ""
            for row in online_list:
                if current_main != row.main:
                    count += 1
                    blob += "\n%s\n" % row.main
                    current_main = row.main

                org_info = ""
                if channel == self.PRIVATE_CHANNEL:
                    if row.org_name:
                        org_info = ", %s of %s" % (row.org_rank_name, row.org_name)

                blob += " | <highlight>%s</highlight> (%d/<green>%d</green>) %s %s%s" % (row.name, row.level or 0, row.ai_level or 0, row.faction, row.profession, org_info)
                if row.online:
                    blob += " [<green>Online</green>]"
                blob += "\n"
            blob += "\n\n"

        return ChatBlob("%s Alts of Online Characters (%d)" % (profession, count), blob)

    def get_online_alts(self, channel, profession):
        sql = "SELECT DISTINCT " \
                "p2.*, " \
                "(CASE WHEN o2.char_id IS NULL THEN 0 ELSE 1 END) AS online, " \
                "COALESCE(p1.name, o.char_id) AS main, " \
                "COALESCE(p2.name, o.char_id) AS name, " \
                "o.channel " \
              "FROM online o " \
              "LEFT JOIN alts a1 ON o.char_id = a1.char_id " \
              "LEFT JOIN alts a2 ON a1.group_id = a2.group_id AND a2.status = ? " \
              "LEFT JOIN player p1 ON p1.char_id = COALESCE(a2.char_id, o.char_id) " \
              "LEFT JOIN alts a3 ON a2.group_id = a3.group_id " \
              "LEFT JOIN player p2 ON p2.char_id = COALESCE(a3.char_id, o.char_id) " \
              "LEFT JOIN online o2 ON p2.char_id = o2.char_id " \
              "WHERE o.channel = ? AND p2.profession = ? " \
              "ORDER BY p1.name ASC, p2.name ASC"

        return self.db.query(sql, [AltsService.MAIN, channel, profession])

    def sort_channels(self, item):
        channel, priority = item
        return str(priority) + channel

    def register_online_channel(self, channel, sort_priority=2):
        if channel not in self.channels:
            self.channels.append((channel, sort_priority))
            self.channels.sort(key=self.sort_channels)

    def deregister_online_channel(self, channel):
        self.db.query("DELETE FROM online WHERE channel = ?", [channel])
        for i, obj in enumerate(self.channels):
            if obj[0] == channel:
                del self.channels[i]
