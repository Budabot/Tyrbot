from core.aochat.bot import Bot
from core.buddy_manager import BuddyManager
from core.character_manager import CharacterManager
from core.public_channel_manager import PublicChannelManager
from core.text import Text
from core.setting_manager import SettingManager
from core.access_manager import AccessManager
from core.decorators import instance
from core.chat_blob import ChatBlob
from core.aochat import server_packets, client_packets


@instance()
class Budabot(Bot):
    def __init__(self):
        super().__init__()
        self.ready = False
        self.packet_handlers = {}
        self.org_id = None
        self.org_name = None
        self.superadmin = None

    def inject(self, registry):
        self.buddy_manager: BuddyManager = registry.get_instance("buddy_manager")
        self.character_manager: CharacterManager = registry.get_instance("character_manager")
        self.public_channel_manager: PublicChannelManager = registry.get_instance("public_channel_manager")
        self.text: Text = registry.get_instance("text")
        self.setting_manager: SettingManager = registry.get_instance("setting_manager")
        self.access_manager: AccessManager = registry.get_instance("access_manager")

    def start(self):
        self.access_manager.register_access_level("superadmin", 1, self.check_superadmin)
        self.setting_manager.register("org_channel_max_page_length", 7500, "")
        self.setting_manager.register("private_message_max_page_length", 7500, "")
        self.setting_manager.register("private_channel_max_page_length", 7500, "")
        self.setting_manager.register("header_color", "", "")
        self.setting_manager.register("header2_color", "", "")
        self.setting_manager.register("highlight_color", "", "")
        self.setting_manager.register("neutral_color", "", "")
        self.setting_manager.register("omni_color", "", "")
        self.setting_manager.register("clan_color", "", "")
        self.setting_manager.register("unknown_color", "", "")
        self.setting_manager.register("symbol", "!", "")

    def check_superadmin(self, char_name):
        return char_name.capitalize() == self.superadmin

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
            if isinstance(packet, server_packets.PrivateMessage):
                self.handle_private_message(packet)
            elif isinstance(packet, server_packets.PublicChannelJoined):
                # set org id and org name
                if packet.channel_id >> 32 == 3:
                    self.org_id = 0x00ffffffff & packet.channel_id
                    if packet.name != "Clan (name unknown)":
                        self.org_name = packet.name

            for handler in self.packet_handlers.get(packet.id, []):
                handler(packet)

            return packet
        else:
            return None

    def send_org_message(self, msg):
        org_channel_id = self.public_channel_manager.org_channel_id
        if org_channel_id is None:
            self.logger.warning("Could not send message to org channel, unknown org id")
        else:
            for page in self.get_text_pages(msg, self.setting_manager.get("org_channel_max_page_length")):
                packet = client_packets.PublicChannelMessage(org_channel_id, page, "")
                self.send_packet(packet)

    def send_private_message(self, char, msg):
        char_id = self.character_manager.resolve_char_to_id(char)
        if char_id is None:
            self.logger.warning("Could not send message to %s, could not find char id" % char)
        else:
            for page in self.get_text_pages(msg, self.setting_manager.get("private_message_max_page_length")):
                self.logger.log_tell("To", self.character_manager.get_char_name(char_id), page)
                packet = client_packets.PrivateMessage(char_id, page, "")
                self.send_packet(packet)

    def send_private_channel_message(self, msg, private_channel=None):
        if private_channel is None:
            private_channel = self.char_id

        private_channel_id = self.character_manager.resolve_char_to_id(private_channel)
        if private_channel_id is None:
            self.logger.warning("Could not send message to private channel %s, could not find private channel" % private_channel)
        else:
            for page in self.get_text_pages(msg, self.setting_manager.get("private_channel_max_page_length")):
                packet = client_packets.PrivateChannelMessage(private_channel_id, page, "")
                self.send_packet(packet)

    def handle_private_message(self, packet: server_packets.PrivateMessage):
        self.logger.log_tell("From", self.character_manager.get_char_name(packet.character_id), packet.message)

    def handle_public_channel_message(self, packet: server_packets.PublicChannelMessage):
        self.logger.log_chat(
            self.public_channel_manager.get_channel_name(packet.channel_id),
            self.character_manager.get_char_name(packet.character_id),
            packet.message)

    def get_text_pages(self, msg, max_page_length):
        if isinstance(msg, ChatBlob):
            return self.text.paginate(msg.title, msg.msg, max_page_length)
        else:
            return [self.text.format_message(msg)]

    def is_ready(self):
        return self.ready
