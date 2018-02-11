from bot import Bot
from buddy_manager import BuddyManager
from character_manager import CharacterManager
from public_channel_manager import PublicChannelManager
from decorators import instance
from chat_blob import ChatBlob
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
        self.text = registry.get_instance("text")

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

    def send_private_message(self, char, msg):
        char_id = self.character_manager.resolve_char_to_id(char)
        if char_id is None:
            self.logger.warning("Could not send message to %s, could not find char id" % char)
        else:
            for page in self.get_text_pages(msg):
                packet = client_packets.PrivateMessage(char_id, page, "")
                self.send_packet(packet)

    def send_private_channel_message(self, msg, private_channel=None):
        private_channel_id = self.private_channel_manager.resolve_char_to_id(private_channel)
        if private_channel_id is None:
            self.logger.warning("Could not send message to private channel %s, could not find private channel" % private_channel)
        else:
            for page in self.get_text_pages(msg):
                packet = client_packets.PrivateChannelMessage(private_channel_id, page, "")
                self.send_packet(packet)

    def handle_private_message(self, packet: server_packets.PrivateMessage):
        self.logger.log_tell("From", self.character_manager.get_char_name(packet.character_id), packet.message)
        pass

    def handle_public_channel_message(self, packet: server_packets.PublicChannelMessage):
        self.logger.log_chat(
            self.public_channel_manager.get_channel_name(packet.channel_id),
            self.character_manager.get_char_name(packet.character_id),
            packet.message)

    def get_text_pages(self, msg):
        if isinstance(msg, ChatBlob):
            return self.text.paginate(msg.title, msg.msg)
        else:
            return [self.text.format_message(msg)]

    def is_ready(self):
        return self.ready
