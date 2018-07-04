from core.decorators import instance, command, event
from core.alts.alts_manager import AltsManager
from core.chat_blob import ChatBlob
from core.private_channel_manager import PrivateChannelManager
import time

@instance()
class OnlineController:
    PRIVATE_CHANNEL = "Private"

    def __init__(self):
        pass

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.pork_manager = registry.get_instance("pork_manager")

    def start(self):
        self.db.exec("DELETE FROM online")

    @command(command="online", params=[], access_level="all",
             description="Show the list of online characters")
    def online_cmd(self, channel, sender, reply, args):
        blob = ""
        count = 0
        for channel in [self.PRIVATE_CHANNEL]:
            online_list = self.get_online_characters(self.PRIVATE_CHANNEL)
            if len(online_list) > 0:
                blob += "<header2>%s Channel<end>\n" % channel

            current_main = ""
            for row in online_list:
                if current_main != row.main:
                    count += 1
                    blob += "\n<highlight>%s<end>\n" % row.main
                    current_main = row.main

                blob += " | <highlight>%s<end> (%d/<green>%d<end>) %s %s\n" % (row.name, row.level or 0, row.ai_level or 0, row.faction, row.profession)

        reply(ChatBlob("Online (%d)" % count, blob))

    @command(command="count", params=[], access_level="all",
             description="Show counts of players by title level, profession, and organization")
    def count_cmd(self, channel, sender, reply, args):
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

        reply(ChatBlob("Count (%d)" % len(data), blob))

    def get_online_characters(self, channel):
        sql = "SELECT p1.*, o.afk, COALESCE(p2.name, p1.name, o.char_id) AS main, IFNULL(p1.name, o.char_id) AS name FROM online o " \
              "LEFT JOIN alts a1 ON o.char_id = a1.char_id " \
              "LEFT JOIN player p1 ON o.char_id = p1.char_id " \
              "LEFT JOIN alts a2 ON a1.group_id = a2.group_id AND a2.status = ? " \
              "LEFT JOIN player p2 ON a2.char_id = p2.char_id " \
              "WHERE channel = ?"

        return self.db.query(sql, [AltsManager.MAIN, channel])

    @event(PrivateChannelManager.JOINED_PRIVATE_CHANNEL_EVENT, "Record in database when someone joins private channel")
    def private_channel_joined_event(self, event_type, event_data):
        self.pork_manager.load_character_info(event_data.char_id)
        self.db.exec("INSERT INTO online (char_id, afk, channel, dt) VALUES (?, ?, ?, ?)",
                     [event_data.char_id, "", self.PRIVATE_CHANNEL, int(time.time())])

    @event(PrivateChannelManager.LEFT_PRIVATE_CHANNEL_EVENT, "Record in database when someone leaves private channel")
    def private_channel_left_event(self, event_type, event_data):
        self.db.exec("DELETE FROM online WHERE char_id = ? AND channel = ?",
                     [event_data.char_id, self.PRIVATE_CHANNEL])
