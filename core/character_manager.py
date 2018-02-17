from core.decorators import instance
from core.aochat.client_packets import CharacterLookup
from core.aochat import server_packets


@instance()
class CharacterManager:
    def __init__(self):
        self.name_to_id = {}
        self.id_to_name = {}

    def inject(self, registry):
        self.bot = registry.get_instance("budabot")

    def start(self):
        self.bot.add_packet_handler(server_packets.CharacterLookup.id, self.update)
        self.bot.add_packet_handler(server_packets.CharacterName.id, self.update)

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
        else:
            return self.get_char_id(char)

    def get_char_name(self, char_id):
        return self.id_to_name.get(char_id, None)

    def update(self, packet):
        self.id_to_name[packet.character_id] = packet.name
        self.name_to_id[packet.name] = packet.character_id
