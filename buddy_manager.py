from registry import instance
from character_manager import CharacterManager


@instance
class BuddyManager:
    def __init__(self):
        self.buddy_list = {}
        self.buddy_list_size = 1000

    def inject(self, get_instance):
        self.character_manager: CharacterManager = get_instance("charactermanager")

    def update(self, packet):
        self.buddy_list[packet.character_id] = {"online": packet.online}

    def get_buddy(self, char):
        char_id = self.character_manager.resolve_char_to_id(char)
        if char_id in self.buddy_list:
            return self.buddy_list[char_id]
        else:
            return None

    def is_online(self, char):
        char_id = self.character_manager.resolve_char_to_id(char)
        buddy = self.get_buddy(char_id)
        if buddy is None:
            return None
        else:
            return buddy["online"] == 1
