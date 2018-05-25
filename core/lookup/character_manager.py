from core.decorators import instance
from core.aochat.client_packets import CharacterLookup
from core.aochat import server_packets
from core.db import DB
import os
import time


@instance()
class CharacterManager:
    def __init__(self):
        self.name_to_id = {}
        self.id_to_name = {}

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")

    def pre_start(self):
        self.bot.add_packet_handler(server_packets.CharacterLookup.id, self.update)
        self.bot.add_packet_handler(server_packets.CharacterName.id, self.update)

    def start(self):
        pass

    def get_char_id(self, char_name):
        char_name = char_name.capitalize()
        if char_name in self.name_to_id:
            return self.name_to_id[char_name]
        else:
            self.bot.send_packet(CharacterLookup(char_name))
            while char_name not in self.name_to_id:
                self.bot.iterate()

            return self.name_to_id.get(char_name, None)

    def resolve_char_to_id(self, char):
        if isinstance(char, int):
            return char
        elif char.isdigit():
            return int(char)
        else:
            return self.get_char_id(char)

    def resolve_char_to_name(self, char):
        if isinstance(char, int):
            return self.get_char_name(char)
        else:
            return char

    def get_char_name(self, char_id):
        return self.id_to_name.get(char_id, None)

    def update(self, packet):
        if packet.char_id == 4294967295:
            self.name_to_id[packet.name] = None
        else:
            self.id_to_name[packet.char_id] = packet.name
            self.name_to_id[packet.name] = packet.char_id
            self._update_name_history(packet.name, packet.char_id)

    def _update_name_history(self, char_name, char_id):
        params = [char_name, char_id, int(time.time())]
        if self.db.type == DB.MYSQL:
            self.db.exec("INSERT IGNORE INTO name_history (name, char_id, created_at) VALUES (?, ?, ?)", params)
        else:
            self.db.exec("INSERT OR IGNORE INTO name_history (name, char_id, created_at) VALUES (?, ?, ?)", params)
