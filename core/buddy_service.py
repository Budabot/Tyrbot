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
        if packet.char_id == 0:
            return

        buddy = conn.buddy_list.get(packet.char_id, {"types": [], "conn_id": conn.id})
        buddy["online"] = packet.online
        conn.buddy_list[packet.char_id] = buddy

        # verify that buddy does not exist on any other conn
        for conn_id, other_conn in self.bot.get_conns():
            if conn.id == conn_id:
                continue

            buddy = other_conn.buddy_list.get(packet.char_id, None)
            if buddy:
                # remove from other conn list
                del other_conn.buddy_list[packet.char_id]

                self.logger.warning("Removing char '%s' from conn '%s' since it already exists on another conn" % (packet.char_id, conn.id))
                other_conn.send_packet(client_packets.BuddyRemove(packet.char_id))

        if packet.online == 1:
            self.event_service.fire_event(self.BUDDY_LOGON_EVENT, packet)
        else:
            self.event_service.fire_event(self.BUDDY_LOGOFF_EVENT, packet)

    def handle_remove(self, conn: Conn, packet):
        if packet.char_id in conn.buddy_list:
            if len(conn.buddy_list[packet.char_id]["types"]) > 0:
                self.logger.warning("Removing buddy %d that still has types %s" % (packet.char_id, conn.buddy_list[packet.char_id]["types"]))

            del conn.buddy_list[packet.char_id]

    def handle_login_ok(self, conn: Conn, packet):
        self.buddy_list_size += 1000
        conn.buddy_list[conn.char_id] = {"online": True, "types": [], "conn_id": conn.id}

    def add_buddy(self, char_id, _type):
        if not char_id:
            return False

        # check if we are trying to add a conn as a buddy
        if self.is_conn_char_id(char_id):
            return False

        buddy = self.get_buddy(char_id)
        if buddy:
            buddy["types"].append(_type)
        else:
            conn = self.get_conn_for_new_buddy()
            conn.send_packet(client_packets.BuddyAdd(char_id, "\1"))
            conn.buddy_list[char_id] = {"online": None, "types": [_type], "conn_id": conn.id}

        return True

    def is_conn_char_id(self, char_id):
        for _id, conn in self.bot.get_conns():
            if conn.char_id == char_id:
                return True

        return False

    def remove_buddy(self, char_id, _type, force_remove=False):
        if not char_id:
            return False

        for _id, conn in self.bot.get_conns():
            if char_id == conn.char_id:
                continue

            buddy = conn.buddy_list.get(char_id, None)
            if buddy:
                if _type in buddy["types"]:
                    buddy["types"].remove(_type)

                if len(buddy["types"]) == 0 or force_remove:
                    conn = self.bot.conns[buddy["conn_id"]]
                    conn.send_packet(client_packets.BuddyRemove(char_id))

        return True

    def get_buddy(self, char_id):
        for _id, conn in self.bot.get_conns():
            if char_id in conn.buddy_list:
                return conn.buddy_list[char_id]
        return None

    def is_online(self, char_id):
        buddy = self.get_buddy(char_id)
        if buddy is None:
            return None
        else:
            return buddy.get("online", None)

    def get_all_buddies(self):
        result = {}
        for _id, conn in self.bot.get_conns():
            for char_id, buddy in conn.buddy_list.items():
                # TODO what if buddies exist on multiple conns?
                result[char_id] = buddy

        return result

    def get_buddy_list_size(self):
        count = 0
        for _id, conn in self.bot.get_conns():
            count += len(conn.buddy_list)

        return count

    def get_conn_for_new_buddy(self):
        buddy_list_size = None
        selected_conn = None
        for _id, conn in self.bot.get_conns():
            if buddy_list_size is None or len(conn.buddy_list) < buddy_list_size:
                buddy_list_size = len(conn.buddy_list)
                selected_conn = conn

        return selected_conn
