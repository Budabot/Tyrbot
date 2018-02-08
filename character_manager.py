class CharacterManager:
    def __init__(self):
        self.name_to_id = {}
        self.id_to_name = {}

    def get_character_id(self, character_name):
        return self.name_to_id[character_name]

    def get_character_name(self, character_id):
        return self.id_to_name[character_id]

    def update(self, packet):
        self.id_to_name[packet.character_id] = packet.name
        self.name_to_id[packet.name] = packet.character_id
