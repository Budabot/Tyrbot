from core.decorators import instance
from core.logger import Logger
from core.aochat import server_packets


@instance()
class TowerController:
    TOWER_BATTLE_OUTCOME_ID = 42949672962
    ALL_TOWERS_ID = 42949672960

    ATTACK_1 = [506, 12753364]
    ATTACK_2 = [506, 147506468]  # 'Notum Wars Update: The %s organization %s lost their base in %s.'
    ATTACK_3 = "(.+) just attacked the (clan|neutral|omni) organization (.+)'s tower in (.+) at location \(\d+, \d+\).\n"

    VICTORY_1 = [42949672962, 0]  # 'The Neutral organization Oldschool attacked the Omni Post Apocalypse at their base in Greater Omni Forest. The attackers won!!', '\x02\x01']

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.event_service = registry.get_instance("event_service")

    def pre_start(self):
        self.event_service.register_event_type("tower_attack")
        self.event_service.register_event_type("tower_victory")
        self.bot.add_packet_handler(server_packets.PublicChannelMessage.id, self.handle_public_channel_message)

    def start(self):
        pass

    def handle_public_channel_message(self, packet: server_packets.PublicChannelMessage):
        if packet.channel_id == self.TOWER_BATTLE_OUTCOME_ID:
            # self.logger.info("tower battle outcome: " + str(packet))
            pass
        elif packet.channel_id == self.ALL_TOWERS_ID:
            if packet.extended_message:
                if [packet.extended_message.category_id, packet.extended_message.instance_id] != self.ATTACK_1:
                    # self.logger.info("tower attack: " + str(packet))
                    pass
                # TODO self.event_service.fire_event("tower_attack", packet.extended_message)
            else:
                # self.logger.warning("No extended message for towers message: " + str(packet))
                pass
