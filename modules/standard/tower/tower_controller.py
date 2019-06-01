from core.chat_blob import ChatBlob
from core.command_param_types import Any, Int
from core.db import DB
from core.decorators import instance, command, event
from core.dict_object import DictObject
from core.event_service import EventService
from core.logger import Logger
from core.aochat import server_packets
from core.lookup.pork_service import PorkService
from core.public_channel_service import PublicChannelService
from core.text import Text
from core.tyrbot import Tyrbot
from modules.standard.helpbot.playfield_controller import PlayfieldController
import re


@instance()
class TowerController:
    TOWER_ATTACK_EVENT = "tower_attack"
    TOWER_VICTORY_EVENT = "tower_victory"

    TOWER_BATTLE_OUTCOME_ID = 42949672962
    ALL_TOWERS_ID = 42949672960

    ATTACK_1 = [506, 12753364]  # The %s organization %s just entered a state of war! %s attacked the %s organization %s's tower in %s at location (%d,%d).
    ATTACK_2 = re.compile(r"^(.+) just attacked the (clan|neutral|omni) organization (.+)'s tower in (.+) at location \((\d+), (\d+)\).\n$")

    VICTORY_1 = re.compile(r"^Notum Wars Update: Victory to the (Clan|Neutral|Omni)s!!!$")
    VICTORY_2 = re.compile(r"^The (Clan|Neutral|Omni) organization (.+) attacked the (Clan|Neutral|Omni) (.+) at their base in (.+). The attackers won!!$")
    VICTORY_3 = [506, 147506468]  # 'Notum Wars Update: The %s organization %s lost their base in %s.'

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.event_service: EventService = registry.get_instance("event_service")
        self.pork_service: PorkService = registry.get_instance("pork_service")
        self.playfield_controller: PlayfieldController = registry.get_instance("playfield_controller")
        self.public_channel_service: PublicChannelService = registry.get_instance("public_channel_service")

    def pre_start(self):
        self.event_service.register_event_type(self.TOWER_ATTACK_EVENT)
        self.event_service.register_event_type(self.TOWER_VICTORY_EVENT)
        self.bot.add_packet_handler(server_packets.PublicChannelMessage.id, self.handle_public_channel_message)

    @command(command="lc", params=[], access_level="all",
             description="See a list of playfields containing land control tower sites")
    def lc_list_cmd(self, request):
        data = self.db.query("SELECT * FROM playfields WHERE id IN (SELECT DISTINCT playfield_id FROM tower_site) ORDER BY short_name")

        blob = ""
        for row in data:
            blob += "%s <highlight>%s<end>\n" % (self.text.make_chatcmd(row.long_name, "/tell <myname> lc %s" % row.short_name), row.short_name)

        return ChatBlob("Land Control Playfields", blob)

    @command(command="lc", params=[Any("playfield"), Int("site_number", is_optional=True)], access_level="all",
             description="See a list of land control tower sites in a particular playfield")
    def lc_playfield_cmd(self, request, playfield_name, site_number):
        playfield = self.playfield_controller.get_playfield_by_name(playfield_name)
        if not playfield:
            return "Could not find playfield <highlight>%s<end>." % playfield_name

        if site_number:
            data = self.db.query("SELECT t.*, p.short_name, p.long_name FROM tower_site t JOIN playfields p ON t.playfield_id = p.id WHERE t.playfield_id = ? AND site_number = ?",
                                 [playfield.id, site_number])
        else:
            data = self.db.query("SELECT t.*, p.short_name, p.long_name FROM tower_site t JOIN playfields p ON t.playfield_id = p.id WHERE t.playfield_id = ?",
                                 [playfield.id])

        if not data:
            if site_number:
                return "Could not find tower info for <highlight>%s %d<end>." % (playfield.long_name, site_number)
            else:
                return "Could not find tower info for <highlight>%s<end>." % playfield.long_name

        blob = ""
        for row in data:
            blob += "<pagebreak>" + self.format_site_info(row) + "\n\n"

        if site_number:
            title = "Tower Info: %s %d" % (playfield.long_name, site_number)
        else:
            title = "Tower Info: %s" % playfield.long_name

        return ChatBlob(title, blob)

    @event(event_type="connect", description="Check if All Towers channel is available", is_hidden=True)
    def handle_connect_event(self, event_type, event_data):
        if self.public_channel_service.org_id and not self.public_channel_service.get_channel_id("All Towers"):
            self.logger.warning("bot is a member of an org but does not have access to 'All Towers' channel and therefore will not receive tower attack messages")

    def format_site_info(self, row):
        blob = "Short name: <highlight>%s %d<end>\n" % (row.short_name, row.site_number)
        blob += "Long name: <highlight>%s, %s<end>\n" % (row.site_name, row.long_name)
        blob += "Level range: <highlight>%d-%d<end>\n" % (row.min_ql, row.max_ql)
        blob += "Coordinates: %s\n" % self.text.make_chatcmd("%dx%d" % (row.x_coord, row.y_coord), "/waypoint %d %d %d" % (row.x_coord, row.y_coord, row.playfield_id))

        return blob

    def handle_public_channel_message(self, packet: server_packets.PublicChannelMessage):
        if packet.channel_id == self.TOWER_BATTLE_OUTCOME_ID:
            victory = self.get_victory_event(packet)

            if victory:
                # self.logger.debug("tower victory packet: %s" % str(packet))

                # lookup playfield
                playfield_name = victory.location.playfield.long_name
                victory.location.playfield = self.playfield_controller.get_playfield_by_name(playfield_name) or DictObject()
                victory.location.playfield.long_name = playfield_name

                self.event_service.fire_event(self.TOWER_VICTORY_EVENT, victory)
        elif packet.channel_id == self.ALL_TOWERS_ID:
            attack = self.get_attack_event(packet)

            if attack:
                # self.logger.debug("tower attack packet: %s" % str(packet))

                # lookup playfield
                playfield_name = attack.location.playfield.long_name
                attack.location.playfield = self.playfield_controller.get_playfield_by_name(playfield_name) or DictObject()
                attack.location.playfield.long_name = playfield_name

                # lookup attacker
                name = attack.attacker.name
                faction = attack.attacker.faction
                org_name = attack.attacker.org_name
                attack.attacker = self.pork_service.get_character_info(name) or DictObject()
                attack.attacker.faction = faction or attack.attacker.get("faction", "Unknown")
                attack.attacker.org_name = org_name

                self.event_service.fire_event(self.TOWER_ATTACK_EVENT, attack)

    def get_attack_event(self, packet: server_packets.PublicChannelMessage):
        if packet.extended_message and [packet.extended_message.category_id, packet.extended_message.instance_id] == self.ATTACK_1:
            params = packet.extended_message.params
            return DictObject({
                "attacker": {
                    "name": params[2],
                    "faction": params[0].capitalize(),
                    "org_name": params[1]
                },
                "defender": {
                    "faction": params[3].capitalize(),
                    "org_name": params[4]
                },
                "location": {
                    "playfield": {
                        "long_name": params[5]
                    },
                    "x_coord": params[6],
                    "y_coord": params[7]
                }
            })
        else:
            match = self.ATTACK_2.match(packet.message)
            if match:
                return DictObject({
                    "attacker": {
                        "name": match.group(1),
                        "faction": "",
                        "org_name": ""
                    },
                    "defender": {
                        "faction": match.group(2).capitalize(),
                        "org_name": match.group(3)
                    },
                    "location": {
                        "playfield": {
                            "long_name": match.group(4)
                        },
                        "x_coord": match.group(5),
                        "y_coord": match.group(6)
                    }
                })

        # Unknown attack
        self.logger.warning("Unknown tower attack: " + str(packet))
        return None

    def get_victory_event(self, packet: server_packets.PublicChannelMessage):
        match = self.VICTORY_1.match(packet.message)
        if match:
            return None

        match = self.VICTORY_2.match(packet.message)
        if match:
            return DictObject({
                "type": "attack",
                "winner": {
                    "faction": match.group(1).capitalize(),
                    "org_name": match.group(2)
                },
                "loser": {
                    "faction": match.group(3).capitalize(),
                    "org_name": match.group(4)
                },
                "location": {
                    "playfield": {
                        "long_name": match.group(5)
                    }
                }
            })

        if packet.extended_message and [packet.extended_message.category_id, packet.extended_message.instance_id] == self.VICTORY_3:
            params = packet.extended_message.params
            return DictObject({
                # TODO might be terminated or un-orged player
                "type": "terminated",
                "winner": {
                    "faction": params[0].capitalize(),
                    "org_name": params[1]
                },
                "loser": {
                    "faction": params[0].capitalize(),
                    "org_name": params[1]
                },
                "location": {
                    "playfield": {
                        "long_name": params[2]
                    }
                }
            })

        # Unknown victory
        self.logger.warning("Unknown tower victory: " + str(packet))
        return None
