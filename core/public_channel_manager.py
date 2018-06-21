from core.decorators import instance
from core.aochat import server_packets


@instance()
class PublicChannelManager:
    def __init__(self):
        self.name_to_id = {}
        self.id_to_name = {}
        self.org_channel_id = None
        self.org_id = None
        self.org_name = None

    def inject(self, registry):
        self.bot = registry.get_instance("bot")

    def pre_start(self):
        self.bot.add_packet_handler(server_packets.PublicChannelJoined.id, self.add)
        self.bot.add_packet_handler(server_packets.PublicChannelLeft.id, self.remove)

    def get_channel_id(self, channel_name):
        return self.name_to_id.get(channel_name, None)

    def get_channel_name(self, channel_id):
        return self.id_to_name[channel_id]

    def add(self, packet: server_packets.PublicChannelJoined):
        self.id_to_name[packet.channel_id] = packet.name
        self.name_to_id[packet.name] = packet.channel_id
        if self.is_org_channel_id(packet.channel_id):
            self.org_channel_id = packet.channel_id
            self.org_id = 0x00ffffffff & packet.channel_id
            if packet.name != "Clan (name unknown)":
                self.org_name = packet.name

    def remove(self, packet: server_packets.PublicChannelLeft):
        channel_name = self.get_channel_name(packet.channel_id)
        del self.id_to_name[packet.channel_id]
        del self.name_to_id[channel_name]

    def is_org_channel_id(self, channel_id):
        return channel_id >> 32 == 3

    def get_org_id(self):
        return self.org_id

    def get_org_name(self):
        return self.org_name
