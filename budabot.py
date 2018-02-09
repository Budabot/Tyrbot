from bot import Bot
from buddy_manager import BuddyManager
from character_manager import CharacterManager
from registry import instance
import logging
import server_packets
import client_packets


@instance
class Budabot(Bot):
    logger = logging.getLogger("Budabot")

    def __init__(self):
        self.public_channels = {}
        self.ready = False
        self.buddy_list_size = 1000
        super().__init__()

    def inject(self, get_instance):
        self.buddy_manager: BuddyManager = get_instance("buddymanager")
        self.character_manager: CharacterManager = get_instance("charactermanager")

    def run(self):
        while None is not self.iterate():
            pass

        self.ready = True

        while True:
            self.iterate()

    def iterate(self):
        packet = self.read_packet()
        if packet is not None:
            print(packet)
            if isinstance(packet, server_packets.PrivateMessage):
                self.handle_private_message(packet)
            elif isinstance(packet, server_packets.CharacterLookup) or isinstance(packet, server_packets.CharacterName):
                self.handle_character_lookup(packet)
            elif isinstance(packet, server_packets.PublicChannelJoined):
                self.handle_public_channel_joined(packet)
            elif isinstance(packet, server_packets.LoginOK):
                self.buddy_list_size += 1000
            elif isinstance(packet, server_packets.BuddyAdded):
                self.handle_buddy_added(packet)
            return packet
        else:
            return None

    def send_org_message(self, message):
        pass

    def send_private_message(self, char, message):
        char_id = self.character_manager.resolve_char_to_id(char)
        if char_id is None:
            self.logger.warning("Could not send message to %s, could not find char id" % char)
        else:
            packet = client_packets.PrivateMessage(char_id, message, "")
            self.send_packet(packet)

    def send_private_channel_message(self, char, message, private_channel=None):
        pass

    def add_buddy(self, char):
        pass

    def remove_buddy(self, char):
        pass

    def handle_private_message(self, packet: server_packets.PrivateMessage):
        pass

    def handle_character_lookup(self, packet):
        self.character_manager.update(packet)

    def handle_public_channel_joined(self, packet: server_packets.PublicChannelJoined):
        self.public_channels[packet.name] = packet.channel_id

    def handle_buddy_added(self, packet):
        self.buddy_manager.update(packet)

    def is_ready(self):
        return self.ready
