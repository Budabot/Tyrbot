from decorators import instance
from character_manager import CharacterManager
import server_packets


@instance
class BuddyManager:
    def __init__(self):
        self.buddy_list = {}
        self.buddy_list_size = 1000

    def inject(self, registry):
        self.character_manager: CharacterManager = registry.get_instance("charactermanager")
        self.bot = registry.get_instance("budabot")

    def start(self):
        self.bot.add_packet_handler(server_packets.BuddyAdded.id, self.add)
        self.bot.add_packet_handler(server_packets.BuddyRemoved.id, self.remove)
        self.bot.add_packet_handler(server_packets.LoginOK.id, self.buddy_list_size)

    def add(self, packet):
        self.buddy_list[packet.character_id] = {"online": packet.online}

    def remove(self, packet):
        del self.buddy_list[packet.character_id]

    def buddy_list_size(self):
        self.buddy_list_size += 1000

    def get_buddy(self, char):
        char_id = self.character_manager.resolve_char_to_id(char)
        return self.buddy_list.get(char_id, None)

    def is_online(self, char):
        char_id = self.character_manager.resolve_char_to_id(char)
        buddy = self.get_buddy(char_id)
        if buddy is None:
            return None
        else:
            return buddy["online"] == 1
