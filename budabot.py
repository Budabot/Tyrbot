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
        super().__init__()
        self.ready = False
        self.packet_handlers = {}

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

    def add_packet_handler(self, packet_id, handler):
        handlers = self.packet_handlers.get(packet_id, [])
        handlers.append(handler)
        self.packet_handlers[packet_id] = handlers

    def iterate(self):
        packet = self.read_packet()
        if packet is not None:
            for handler in self.packet_handlers.get(packet.id, []):
                handler(packet)

            if isinstance(packet, server_packets.PrivateMessage):
                self.handle_private_message(packet)

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

    def handle_private_message(self, packet: server_packets.PrivateMessage):
        self.logger.log_tell("From", self.character_manager.get_char_name(packet.character_id), packet.message)
        pass

    def handle_public_channel_message(self, packet: server_packets.PublicChannelMessage):
        self.logger.log_chat(
            self.public_channel_manager.get_channel_name(packet.channel_id),
            self.character_manager.get_char_name(packet.character_id),
            packet.message)

    def is_ready(self):
        return self.ready
