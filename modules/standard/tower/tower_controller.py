from core.decorators import instance
from core.logger import Logger
from core.aochat import server_packets
from core.aochat.extended_message import ExtendedMessage


@instance()
class TowerController:
    TOWER_BATTLE_OUTCOME_ID = 42949672962
    ALL_TOWERS_ID = 1

    def __init__(self):
        self.logger = Logger("tower_controller")

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.event_manager = registry.get_instance("event_manager")
        self.mmdb = registry.get_instance("mmdb_parser")

    def pre_start(self):
        self.event_manager.register_event_type("tower_attack")
        self.event_manager.register_event_type("tower_victory")
        self.bot.add_packet_handler(server_packets.PublicChannelMessage.id, self.handle_public_channel_message)

    def start(self):
        pass

    def handle_public_channel_message(self, packet: server_packets.PublicChannelMessage):
        if packet.channel_id == self.TOWER_BATTLE_OUTCOME_ID:
            print("tower battle outcome", packet)
        elif packet.channel_id == self.ALL_TOWERS_ID:
            print("tower attack", packet)
            msg = packet.message
            if msg.startswith("~&") and msg.endswith("~"):
                msg = msg[1:-2]
                category_id = self.mmdb.read_base_85(msg[0:5])
                instance_id = self.mmdb.read_base_85(msg[5: 10])
                template = self.mmdb.get_message_string(category_id, instance_id)
                params = self.mmdb.parse_params(msg[10:])
                extended_message = ExtendedMessage(category_id, instance_id, template, params)
                print(extended_message)
                print(extended_message.get_message())
                self.event_manager.fire_event("tower_attack", extended_message)
            else:
                raise Exception("Tower message not an extended message")
