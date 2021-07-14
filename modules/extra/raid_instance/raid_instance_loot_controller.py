import time
from collections import OrderedDict

from core.conn import Conn
from core.decorators import instance
from modules.standard.raid.loot_controller import LootController


@instance("loot_controller", override=True)
class RaidInstanceLootController(LootController):
    def update_last_modify(self, conn: Conn):
        conn.data.loot_last_modify = int(time.time())

    def clear_last_modify(self, conn: Conn):
        conn.data.loot_last_modify = 0

    def get_last_modify(self, conn: Conn):
        if not conn.data.get("loot_last_modify"):
            self.clear_last_modify(conn)

        return conn.data.loot_last_modify

    def clear_loot_list(self, conn: Conn):
        conn.data.loot_list = OrderedDict()

    def get_loot_list(self, conn: Conn):
        if not conn.data.get("loot_list"):
            self.clear_loot_list(conn)

        return conn.data.loot_list

    def send_loot_message(self, msg, conn):
        self.bot.send_private_channel_message(msg, conn=conn)
