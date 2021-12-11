from core.decorators import instance
from core.aochat.client_packets import CharacterLookup
from core.aochat import server_packets
import time


@instance()
class CharacterService:
    SYSTEM_CHAR_ID = 4294967295

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

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS name_history (char_id BIGINT NOT NULL, name VARCHAR(20) NOT NULL, created_at INT NOT NULL, PRIMARY KEY (char_id, name))")

    def _wait_for_char_id(self, char_name):
        # char_name must be .capitalize()'ed

        packet = self.bot.iterate(1)
        while packet and char_name not in self.name_to_id:
            packet = self.bot.iterate(1)

        return self.name_to_id.get(char_name, None)

    def resolve_char_to_id(self, char_name_or_id):
        if isinstance(char_name_or_id, int):
            return char_name_or_id
        elif char_name_or_id.isdigit():
            return int(char_name_or_id)
        else:
            char_name = char_name_or_id.capitalize()
            if char_name in self.name_to_id:
                return self.name_to_id[char_name]
            else:
                self._send_lookup_if_needed(char_name)
                return self._wait_for_char_id(char_name)

    def resolve_char_to_name(self, char_name_or_id, default=None):
        if isinstance(char_name_or_id, int) or char_name_or_id.isdigit():
            char_name = self.get_char_name(char_name_or_id)
            return char_name if char_name else default
        else:
            return char_name_or_id

    def get_char_name(self, char_id):
        return self.id_to_name.get(char_id, None)

    def update(self, conn, packet):
        self.waiting_for_response.discard(packet.name)

        if packet.char_id == self.SYSTEM_CHAR_ID:
            self.name_to_id[packet.name] = None
        else:
            self.id_to_name[packet.char_id] = packet.name
            self.name_to_id[packet.name] = packet.char_id
            self._update_name_history(packet.name, packet.char_id)

    def _update_name_history(self, char_name, char_id):
        params = [char_name, char_id, int(time.time())]
        self.db.exec("INSERT IGNORE INTO name_history (name, char_id, created_at) VALUES (?, ?, ?)", params)

    def _send_lookup_if_needed(self, char_name):
        # char_name must be .capitalize()'ed
        if char_name not in self.name_to_id and char_name not in self.waiting_for_response:
            self.waiting_for_response.add(char_name)
            # TODO load balance over all conns?
            self.bot.get_primary_conn().send_packet(CharacterLookup(char_name))
