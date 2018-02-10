from registry import instance


@instance
class PublicChannelManager:
    def __init__(self):
        self.name_to_id = {}
        self.id_to_name = {}

    def inject(self, registry):
        self.bot = registry.get_instance("budabot")

    def start(self):
        pass

    def get_channel_id(self, channel_name):
        return self.name_to_id.get(channel_name, None)

    def get_channel_name(self, channel_id):
        return self.id_to_name[channel_id]

    def add(self, packet):
        self.id_to_name[packet.channel_id] = packet.name
        self.name_to_id[packet.name] = packet.channel_id

    def remove(self, packet):
        channel_name = self.get_channel_name(packet.channel_id)
        del self.id_to_name[packet.channel_id]
        del self.name_to_id[channel_name]
