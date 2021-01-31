import threading

from core.decorators import instance
from core.aochat.client_packets import CharacterLookup
from core.aochat import server_packets
import time

from core.feature_flags import FeatureFlags


@instance()
class CharacterService:
    def __init__(self):
        self.name_to_id = {}
        self.id_to_name = {}
        self.waiting_for_response = set()
        self.notify_on_receive = {}

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")

    def pre_start(self):
        self.bot.register_packet_handler(server_packets.CharacterLookup.id, self.update)
        self.bot.register_packet_handler(server_packets.CharacterName.id, self.update)

    def _wait_for_char_id(self, char_name):
        # char_name must be .capitalize()'ed

        packet = self.bot.iterate(1)
        while packet and char_name not in self.name_to_id:
            packet = self.bot.iterate(1)

        return self.name_to_id.get(char_name, None)

    # FeatureFlags.THREADING
    def _wait_for_char_id_threading(self, char_name):
        # char_name must be .capitalize()'ed

        event = self.notify_on_receive.get(char_name, None)
        if event is None:
            event = threading.Event()
            self.notify_on_receive[char_name] = event

        if char_name not in self.name_to_id:
            event.wait(10)

        return self.name_to_id.get(char_name, None)

    def resolve_char_to_id(self, char):
        if isinstance(char, int):
            return char
        elif char.isdigit():
            return int(char)
        else:
            char_name = char.capitalize()
            if char_name in self.name_to_id:
                return self.name_to_id[char_name]
            else:
                self._send_lookup_if_needed(char_name)
                if FeatureFlags.THREADING:
                    return self._wait_for_char_id_threading(char_name)
                else:
                    return self._wait_for_char_id(char_name)

    def resolve_char_to_name(self, char, default=None):
        if isinstance(char, int) or char.isdigit():
            char_name = self.get_char_name(char)
            return char_name if char_name else default
        else:
            return char

    def get_char_name(self, char_id):
        return self.id_to_name.get(char_id, None)

    def update(self, packet):
        self.waiting_for_response.discard(packet.name)

        if packet.char_id == 4294967295:
            self.name_to_id[packet.name] = None
        else:
            self.id_to_name[packet.char_id] = packet.name
            self.name_to_id[packet.name] = packet.char_id
            self._update_name_history(packet.name, packet.char_id)

        if FeatureFlags.THREADING:
            event = self.notify_on_receive.pop(packet.name, None)
            if event:
                event.set()

    def _update_name_history(self, char_name, char_id):
        params = [char_name, char_id, int(time.time())]
        self.db.exec("INSERT IGNORE INTO name_history (name, char_id, created_at) VALUES (?, ?, ?)", params)

    def _send_lookup_if_needed(self, char_name):
        # char_name must be .capitalize()'ed
        if char_name not in self.name_to_id and char_name not in self.waiting_for_response:
            self.waiting_for_response.add(char_name)
            self.bot.send_packet(CharacterLookup(char_name))
