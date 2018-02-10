from registry import instance
from client_packets import CharacterLookup


@instance
class CharacterManager:
    def __init__(self):
        self.name_to_id = {}
        self.id_to_name = {}

    def inject(self, registry):
        self.bot = registry.get_instance("budabot")

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

            if char_name in self.name_to_id:
                return self.name_to_id[char_name]
            else:
                return None

    def resolve_char_to_id(self, char):
        if isinstance(char, int):
            return char
        else:
            return self.get_char_id(char)

    def get_char_name(self, char_id):
        return self.id_to_name[char_id]

    def update(self, packet):
        self.id_to_name[packet.character_id] = packet.name
        self.name_to_id[packet.name] = packet.character_id
