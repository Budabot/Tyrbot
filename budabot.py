from bot import Bot
from buddy_manager import BuddyManager
from character_manager import CharacterManager
from public_channel_manager import PublicChannelManager
from registry import instance
import server_packets
import client_packets


@instance
class Budabot(Bot):
    def __init__(self):
        self.ready = False
        super().__init__()

    def inject(self, registry):
        self.buddy_manager: BuddyManager = registry.get_instance("buddymanager")
        self.character_manager: CharacterManager = registry.get_instance("charactermanager")
        self.public_channel_manager: PublicChannelManager = registry.get_instance("publicchannelmanager")

    def start(self):
        pass

    def run(self):
        while None is not self.iterate():
            pass

        self.ready = True

        while True:
            self.iterate()

    def iterate(self):
        packet = self.read_packet()
        if packet is not None:
            if isinstance(packet, server_packets.PrivateMessage):
                self.handle_private_message(packet)

            elif isinstance(packet, server_packets.CharacterLookup) or isinstance(packet, server_packets.CharacterName):
                self.handle_character_lookup(packet)

            elif isinstance(packet, server_packets.PublicChannelJoined):
                self.handle_public_channel_joined(packet)

            elif isinstance(packet, server_packets.PublicChannelLeft):
                self.handle_public_channel_left(packet)

            elif isinstance(packet, server_packets.LoginOK):
                self.buddy_manager.buddy_list_size += 1000

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
        self.logger.log_tell("From", self.character_manager.get_char_name(packet.character_id), packet.message)
        pass

    def handle_public_channel_message(self, packet: server_packets.PublicChannelMessage):
        self.logger.log_chat(
            self.public_channel_manager.get_channel_name(packet.channel_id),
            self.character_manager.get_char_name(packet.character_id),
            packet.message)

    def handle_character_lookup(self, packet):
        self.character_manager.update(packet)

    def handle_public_channel_joined(self, packet: server_packets.PublicChannelJoined):
        self.public_channel_manager.add(packet)

    def handle_public_channel_left(self, packet: server_packets.PublicChannelLeft):
        self.public_channel_manager.remove(packet)

    def handle_buddy_added(self, packet):
        self.buddy_manager.update(packet)

    def is_ready(self):
        return self.ready
