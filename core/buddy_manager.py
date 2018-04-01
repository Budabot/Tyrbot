from core.decorators import instance
from core.character_manager import CharacterManager
from core.aochat import server_packets
from core.aochat import client_packets


@instance()
class BuddyManager:
    def __init__(self):
        self.buddy_list = {}
        self.buddy_list_size = 1000

    def inject(self, registry):
        self.character_manager: CharacterManager = registry.get_instance("character_manager")
        self.bot = registry.get_instance("budabot")
        self.event_manager = registry.get_instance("event_manager")

    def start(self):
        self.bot.add_packet_handler(server_packets.BuddyAdded.id, self.handle_add)
        self.bot.add_packet_handler(server_packets.BuddyRemoved.id, self.handle_remove)
        self.bot.add_packet_handler(server_packets.LoginOK.id, self.handle_login_ok)
        self.event_manager.register_event_type("buddy_logon")
        self.event_manager.register_event_type("buddy_logoff")

    def handle_add(self, packet):
        buddy = self.buddy_list.get(packet.character_id, {})
        buddy["online"] = packet.online
        self.buddy_list[packet.character_id] = buddy
        if packet.online == 1:
            self.event_manager.fire_event("buddy_logon", packet)
        else:
            self.event_manager.fire_event("buddy_logoff", packet)

    def handle_remove(self, packet):
        del self.buddy_list[packet.character_id]

    def handle_login_ok(self):
        self.buddy_list_size += 1000

    def add_buddy(self, char, _type):
        char_id = self.character_manager.resolve_char_to_id(char)
        if char_id:
            if char_id not in self.buddy_list:
                self.bot.send_packet(client_packets.BuddyAdd(char_id, "1"))  # TODO b"1"
                self.buddy_list[char_id] = {"online": None, "types": set(_type)}
            else:
                self.buddy_list[char_id]["types"].append(_type)

            return True
        else:
            return False

    def remove_buddy(self, char, _type):
        char_id = self.character_manager.resolve_char_to_id(char)
        if char_id:
            if char_id not in self.buddy_list:
                return False
            else:
                self.buddy_list[char_id]["types"].remove(_type)
                if len(self.buddy_list[char_id]["types"]) == 0:
                    del self.buddy_list[char_id]
                    self.bot.send_packet(client_packets.BuddyRemove(char_id))
                return True
        else:
            return False

    def get_buddy(self, char):
        char_id = self.character_manager.resolve_char_to_id(char)
        return self.buddy_list.get(char_id, None)

    def is_online(self, char):
        char_id = self.character_manager.resolve_char_to_id(char)
        buddy = self.get_buddy(char_id)
        if buddy is None:
            return None
        else:
            return buddy.get("online", None)
