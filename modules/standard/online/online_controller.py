from core.decorators import instance, command, event
from core.alts.alts_service import AltsService
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

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.pork_service = registry.get_instance("pork_service")
        self.character_service = registry.get_instance("character_service")
        self.discord_controller = registry.get_instance("discord_controller")

    def start(self):
        self.db.exec("DELETE FROM online")
        self.discord_controller.register_discord_command_handler(self.online_discord_cmd, "online", [])

    @command(command="online", params=[], access_level="all",
             description="Show the list of online characters", aliases=["o"])
    def online_cmd(self, channel, sender, reply):
        blob = ""
        count = 0
        for channel in [self.ORG_CHANNEL, self.PRIVATE_CHANNEL]:
            online_list = self.get_online_characters(channel)
            if len(online_list) > 0:
                blob += "<header2>%s Channel<end>\n" % channel

            current_main = ""
            for row in online_list:
                if current_main != row.main:
                    count += 1
                    blob += "\n<highlight>%s<end>\n" % row.main
                    current_main = row.main

                afk = ""
                if row.afk_dt > 0:
                    afk = " - <highlight>%s (%s ago)<end>" % (row.afk_reason, self.util.time_to_readable(int(time.time()) - row.afk_dt))

                blob += " | <highlight>%s<end> (%d/<green>%d<end>) %s %s%s\n" % (row.name, row.level or 0, row.ai_level or 0, row.faction, row.profession, afk)
            blob += "\n\n"

        return ChatBlob("Online (%d)" % count, blob)

    @command(command="count", params=[], access_level="all",
             description="Show counts of players by title level, profession, and organization")
    def count_cmd(self, channel, sender, reply):
        data = self.db.query("SELECT p.*, o.channel, COALESCE(p.name, o.char_id) AS name FROM online o LEFT JOIN player p ON o.char_id = p.char_id ORDER BY channel ASC")

        title_levels = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
        profs = {"Adventurer": 0, "Agent": 0, "Bureaucrat": 0, "Doctor": 0, "Enforcer": 0, "Engineer": 0, "Fixer": 0, "Keeper": 0,
                 "Martial Artist": 0, "Meta-Physicist": 0, "Nano-Technician": 0, "Soldier": 0, "Trader": 0, "Shade": 0}
        orgs = {}

        # populate counts
        for row in data:
            profs[row.profession] += 1
            title_levels[self.util.get_title_level(row.level)] += 1
            org_name = row.org_name if row.org_name else "&lt;None&gt;"
            org_count = orgs.get(org_name, 0)
            orgs[org_name] = org_count + 1

        blob = ""
        blob += "<header>Title Levels<end>\n"
        for title_level, count in title_levels.items():
            if count > 0:
                blob += "%d: %d\n" % (title_level, count)

        blob += "\n\n<header>Professions<end>\n"
        for prof, count in profs.items():
            if count > 0:
                blob += "%s: %d\n" % (prof, count)

        blob += "\n\n<header>Organizations<end>\n"
        for org, count in orgs.items():
            if count > 0:
                blob += "%s: %d\n" % (org, count)

        return ChatBlob("Count (%d)" % len(data), blob)

    def get_online_characters(self, channel):
        sql = "SELECT p1.*, o.afk_dt, o.afk_reason, COALESCE(p2.name, p1.name, o.char_id) AS main, IFNULL(p1.name, o.char_id) AS name FROM online o " \
              "LEFT JOIN alts a1 ON o.char_id = a1.char_id " \
              "LEFT JOIN player p1 ON o.char_id = p1.char_id " \
              "LEFT JOIN alts a2 ON a1.group_id = a2.group_id AND a2.status = ? " \
              "LEFT JOIN player p2 ON a2.char_id = p2.char_id " \
              "WHERE channel = ?"

        return self.db.query(sql, [AltsService.MAIN, channel])

    @event(PrivateChannelService.JOINED_PRIVATE_CHANNEL_EVENT, "Record in database when someone joins private channel")
    def private_channel_joined_event(self, event_type, event_data):
        self.pork_service.load_character_info(event_data.char_id)
        self.db.exec("INSERT INTO online (char_id, afk_dt, afk_reason, channel, dt) VALUES (?, ?, ?, ?, ?)",
                     [event_data.char_id, 0, "", self.PRIVATE_CHANNEL, int(time.time())])

    @event(PrivateChannelService.LEFT_PRIVATE_CHANNEL_EVENT, "Record in database when someone leaves private channel")
    def private_channel_left_event(self, event_type, event_data):
        self.db.exec("DELETE FROM online WHERE char_id = ? AND channel = ?",
                     [event_data.char_id, self.PRIVATE_CHANNEL])

    @event(OrgMemberController.ORG_MEMBER_LOGON_EVENT, "Record in database when org member logs on")
    def org_member_logon_event(self, event_type, event_data):
        self.pork_service.load_character_info(event_data.char_id)
        self.db.exec("INSERT INTO online (char_id, afk_dt, afk_reason, channel, dt) VALUES (?, ?, ?, ?, ?)",
                     [event_data.char_id, 0, "", self.ORG_CHANNEL, int(time.time())])

    @event(OrgMemberController.ORG_MEMBER_LOGOFF_EVENT, "Record in database when org member logs off")
    def org_member_logoff_event(self, event_type, event_data):
        self.db.exec("DELETE FROM online WHERE char_id = ? AND channel = ?",
                     [event_data.char_id, self.ORG_CHANNEL])

    @event(PrivateChannelService.PRIVATE_CHANNEL_MESSAGE_EVENT, "Check for afk messages in private channel")
    def afk_check_private_channel_event(self, event_type, event_data):
        if event_data.char_id != self.bot.char_id:
            self.afk_check(event_data.char_id, event_data.message, lambda msg: self.bot.send_private_channel_message(msg))

    @event(PublicChannelService.ORG_MESSAGE_EVENT, "Check for afk messages in org channel")
    def afk_check_org_channel_event(self, event_type, event_data):
        if event_data.char_id != self.bot.char_id:
            self.afk_check(event_data.char_id, event_data.message, lambda msg: self.bot.send_org_message(msg))

    def afk_check(self, char_id, message, channel_reply):
        matches = self.afk_regex.search(message)
        if matches:
            char_name = self.character_service.resolve_char_to_name(char_id)
            self.set_afk(char_id, int(time.time()), message)
            channel_reply("<highlight>%s<end> is now afk." % char_name)
        else:
            row = self.db.query_single("SELECT * FROM online WHERE char_id = ? AND afk_dt > 0", [char_id])
            if row:
                self.set_afk(char_id, 0, "")
                char_name = self.character_service.resolve_char_to_name(char_id)
                time_string = self.util.time_to_readable(int(time.time()) - row.afk_dt)
                channel_reply("<highlight>%s<end> is back after %s." % (char_name, time_string))

    def set_afk(self, char_id, dt, reason):
        self.db.exec("UPDATE online SET afk_dt = ?, afk_reason = ? WHERE char_id = ?", [dt, reason, char_id])

    def online_discord_cmd(self, reply, args):
        blob = ""
        count = 0

        online_list = self.get_online_characters("Private")

        current_main = ""
        for row in online_list:
            if current_main != row.main:
                count += 1
                blob += "\n[%s]\n" % row.main
                current_main = row.main

            blob += " | %s (%d/%d) %s %s\n" % (row.name, row.level or 0, row.ai_level or 0, row.faction, row.profession)

        reply(blob)
