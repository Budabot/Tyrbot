from core.decorators import instance, command, event
from core.alts.alts_manager import AltsManager
from core.chat_blob import ChatBlob
from core.private_channel_manager import PrivateChannelManager
import os
import time


@instance()
class OnlineController:
    PRIVATE_CHANNEL = "Private"

    def __init__(self):
        pass

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.pork_manager = registry.get_instance("pork_manager")

    def start(self):
        self.db.load_sql_file("online.sql", os.path.dirname(__file__))

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

                blob += " | <highlight>%s<end> (%d/<green>%d<end>) %s %s\n" % (row.name, row.level, row.ai_level, row.faction, row.profession)

        reply(ChatBlob("Online (%d)" % count, blob))

    def get_online_characters(self, channel):
        sql = "SELECT p1.*, o.afk, COALESCE(p2.name, p1.name) AS main FROM online o " \
              "LEFT JOIN alts a1 ON o.char_id = a1.char_id " \
              "LEFT JOIN player p1 ON o.char_id = p1.char_id " \
              "LEFT JOIN alts a2 ON a1.group_id = a2.group_id AND a2.status = ? " \
              "LEFT JOIN player p2 ON a2.char_id = p2.char_id " \
              "WHERE channel = ?"

        return self.db.query(sql, [AltsManager.MAIN, channel])

    @event(PrivateChannelManager.JOINED_PRIVATE_CHANNEL_EVENT, "Record in database when someone joins private channel")
    def private_channel_joined_event(self, event_type, event_data):
        self.pork_manager.load_character_info(event_data.character_id)
        self.db.exec("INSERT INTO online (char_id, afk, channel, dt) VALUES (?, ?, ?, ?)",
                     [event_data.character_id, "", self.PRIVATE_CHANNEL, int(time.time())])

    @event(PrivateChannelManager.LEFT_PRIVATE_CHANNEL_EVENT, "Record in database when someone leaves private channel")
    def private_channel_left_event(self, event_type, event_data):
        self.db.exec("DELETE FROM online WHERE char_id = ? AND channel = ?",
                     [event_data.character_id, self.PRIVATE_CHANNEL])
