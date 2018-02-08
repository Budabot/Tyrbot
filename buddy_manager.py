class BuddyManager:
    def __init__(self):
        self.buddy_list = {}

    def update(self, packet):
        self.buddy_list[packet.character_id] = packet.online

    def get_buddy(self, character_id):
        if character_id in self.buddy_list:
            return self.buddy_list[character_id]
        else:
            return None

    def is_online(self, character_id):
        buddy = self.get_buddy(character_id)
        if buddy is None:
            return None
        else:
            return buddy == 1
