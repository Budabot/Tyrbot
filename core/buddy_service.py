from core.conn import Conn
from core.decorators import instance
from core.lookup.character_service import CharacterService
from core.aochat import server_packets
from core.aochat import client_packets
from core.logger import Logger


@instance()
class BuddyService:
    BUDDY_LOGON_EVENT = "buddy_logon"
    BUDDY_LOGOFF_EVENT = "buddy_logoff"

    def __init__(self):
        self.buddy_list = {}
        self.buddy_list_size = 0
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.bot = registry.get_instance("bot")
        self.event_service = registry.get_instance("event_service")

    def pre_start(self):
        self.bot.register_packet_handler(server_packets.BuddyAdded.id, self.handle_add)
        self.bot.register_packet_handler(server_packets.BuddyRemoved.id, self.handle_remove)
        self.bot.register_packet_handler(server_packets.LoginOK.id, self.handle_login_ok)
        self.event_service.register_event_type(self.BUDDY_LOGON_EVENT)
        self.event_service.register_event_type(self.BUDDY_LOGOFF_EVENT)

    def handle_add(self, conn: Conn, packet):
        buddy = self.buddy_list[conn.id].get(packet.char_id, {"types": [], "conn_id": conn.id})
        buddy["online"] = packet.online
        self.buddy_list[conn.id][packet.char_id] = buddy

        if packet.online == 1:
            self.event_service.fire_event(self.BUDDY_LOGON_EVENT, packet)
        else:
            self.event_service.fire_event(self.BUDDY_LOGOFF_EVENT, packet)

    def handle_remove(self, conn: Conn, packet):
        conn_buddy_list = self.buddy_list[conn.id]
        if packet.char_id in conn_buddy_list:
            if len(conn_buddy_list[packet.char_id]["types"]) > 0:
                self.logger.warning("Removing buddy %d that still has types %s" % (packet.char_id, conn_buddy_list[packet.char_id]["types"]))

            del conn_buddy_list[packet.char_id]

    def handle_login_ok(self, conn: Conn, packet):
        self.buddy_list_size += 1000
        self.buddy_list[conn.id] = {}

    def add_buddy(self, char_id, _type):
        if not char_id:
            return False

        # check if we are trying to add a conn as a buddy
        if char_id in self.buddy_list:
            return False

        buddy = self.get_buddy(char_id)
        if buddy:
            buddy["types"].append(_type)
        else:
            conn = self.get_conn_for_new_buddy()
            if not conn:
                self.logger.warning(f"Could not add buddy '{char_id}' with type '{_type}' since buddy list is full")
            else:
                conn.send_packet(client_packets.BuddyAdd(char_id, "\1"))
                self.buddy_list[conn.id][char_id] = {"online": None, "types": [_type], "conn_id": conn.id}

        return True

    def remove_buddy(self, char_id, _type, force_remove=False):
        if char_id:
            buddy = self.get_buddy(char_id)
            if not buddy:
                return False

            if _type in buddy["types"]:
                buddy["types"].remove(_type)

            if len(buddy["types"]) == 0 or force_remove:
                conn = self.bot.conns[buddy["conn_id"]]
                conn.send_packet(client_packets.BuddyRemove(char_id))

            return True
        else:
            return False

    def get_buddy(self, char_id):
        # if char is conn
        if char_id in self.buddy_list:
            return {
                "online": True,
                "types": []
            }

        for conn_id, conn_buddy_list in self.buddy_list.items():
            if char_id in conn_buddy_list:
                return conn_buddy_list[char_id]
        return None

    def is_online(self, char_id):
        buddy = self.get_buddy(char_id)
        if buddy is None:
            return None
        else:
            return buddy.get("online", None)

    def get_all_buddies(self):
        result = {}
        for conn_id, conn_buddy_list in self.buddy_list.items():
            for char_id, buddy in conn_buddy_list.items():
                # TODO what if buddies exist on multiple conns?
                result[char_id] = buddy

        return result

    def get_buddy_list_size(self):
        count = 0
        for conn_id, conn_buddy_list in self.buddy_list.items():
            count += len(conn_buddy_list)

        return count

    def get_conn_for_new_buddy(self):
        buddy_list_size = 1001
        _id = None
        for conn_id, conn_buddy_list in self.buddy_list.items():
            if len(conn_buddy_list) < buddy_list_size:
                buddy_list_size = len(conn_buddy_list)
                _id = conn_id

        return self.bot.conns.get(_id, None)
