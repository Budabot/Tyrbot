from bot import Bot
from buddy_manager import BuddyManager
from character_manager import CharacterManager
import server_packets
import client_packets


class Budabot(Bot):
    def __init__(self):
        self.public_channels = {}
        self.ready = False
        self.buddy_list_size = 1000
        self.buddy_manager = BuddyManager()
        self.character_manager = CharacterManager()
        super().__init__()

    def run(self):
        while True:
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
            else:
                self.ready = True

    def send_org_message(self, message):
        pass

    def send_private_message(self, character_name, message):
        # TODO
        character_id = self.character_manager.get_character_id(character_name)
        packet = client_packets.PrivateMessage(character_id, message, "")
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
