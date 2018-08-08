from core.decorators import instance
from core.event_service import EventService
from core.lookup.character_service import CharacterService
from core.aochat import server_packets
from core.aochat import client_packets
from core.logger import Logger
from core.tyrbot import Tyrbot


@instance()
class BuddyService:
    BUDDY_LOGON_EVENT = "buddy_logon"
    BUDDY_LOGOFF_EVENT = "buddy_logoff"

    def __init__(self):
        self.buddy_list = {}
        self.buddy_list_size = 1000
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.event_service: EventService = registry.get_instance("event_service")

    def pre_start(self):
        self.bot.add_packet_handler(server_packets.BuddyAdded.id, self.handle_add)
        self.bot.add_packet_handler(server_packets.BuddyRemoved.id, self.handle_remove)
        self.bot.add_packet_handler(server_packets.LoginOK.id, self.handle_login_ok)
        self.event_service.register_event_type(self.BUDDY_LOGON_EVENT)
        self.event_service.register_event_type(self.BUDDY_LOGOFF_EVENT)

    def handle_add(self, packet):
        buddy = self.buddy_list.get(packet.char_id, {"types": []})
        buddy["online"] = packet.online
        self.buddy_list[packet.char_id] = buddy
        if packet.online == 1:
            self.event_service.fire_event(self.BUDDY_LOGON_EVENT, packet)
        else:
            self.event_service.fire_event(self.BUDDY_LOGOFF_EVENT, packet)

    def handle_remove(self, packet):
        if packet.char_id in self.buddy_list:
            if len(self.buddy_list[packet.char_id]["types"]) > 0:
                self.logger.warning("Removing buddy %d that still has types %s" % (packet.char_id, self.buddy_list[packet.char_id]["types"]))
            del self.buddy_list[packet.char_id]

    def handle_login_ok(self, packet):
        self.buddy_list_size += 1000

    def add_buddy(self, char_id, _type):
        if char_id and char_id != self.bot.char_id:
            if char_id not in self.buddy_list:
                self.bot.send_packet(client_packets.BuddyAdd(char_id, "\1"))
                self.buddy_list[char_id] = {"online": None, "types": [_type]}
            elif _type not in self.buddy_list[char_id]["types"]:
                self.buddy_list[char_id]["types"].append(_type)

            return True
        else:
            return False

    def remove_buddy(self, char_id, _type, force_remove=False):
        if char_id:
            if char_id not in self.buddy_list:
                return False
            else:
                if _type in self.buddy_list[char_id]["types"]:
                    self.buddy_list[char_id]["types"].remove(_type)
                if len(self.buddy_list[char_id]["types"]) == 0 or force_remove:
                    self.bot.send_packet(client_packets.BuddyRemove(char_id))
                return True
        else:
            return False

    def get_buddy(self, char_id):
        # if char is bot
        if char_id == self.bot.char_id:
            return {
                "online": True,
                "types": []
            }

        return self.buddy_list.get(char_id, None)

    def is_online(self, char_id):
        buddy = self.get_buddy(char_id)
        if buddy is None:
            return None
        else:
            return buddy.get("online", None)

    def get_all_buddies(self):
        return dict(self.buddy_list)
