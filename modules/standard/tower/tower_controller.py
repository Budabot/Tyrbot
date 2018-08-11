from core.chat_blob import ChatBlob
from core.command_param_types import Any
from core.decorators import instance, command
from core.dict_object import DictObject
from core.logger import Logger
from core.aochat import server_packets
import re


@instance()
class TowerController:
    TOWER_ATTACK_EVENT = "tower_attack"
    TOWER_VICTORY_EVENT = "tower_victory"

    TOWER_BATTLE_OUTCOME_ID = 42949672962
    ALL_TOWERS_ID = 42949672960

    ATTACK_1 = [506, 12753364]  # The %s organization %s just entered a state of war! %s attacked the %s organization %s's tower in %s at location (%d,%d).
    ATTACK_2 = [506, 147506468]  # 'Notum Wars Update: The %s organization %s lost their base in %s.'
    ATTACK_3 = re.compile("^(.+) just attacked the (clan|neutral|omni) organization (.+)'s tower in (.+) at location \(\d+, \d+\).\n$")

    VICTORY_1 = re.compile("^The (Clan|Neutral|Omni) organization (.+) attacked the (Clan|Neutral|Omni) (.+) at their base in (.+). The attackers won!!$")

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.event_service = registry.get_instance("event_service")
        self.playfield_controller = registry.get_instance("playfield_controller")

    def pre_start(self):
        self.event_service.register_event_type(self.TOWER_ATTACK_EVENT)
        self.event_service.register_event_type(self.TOWER_VICTORY_EVENT)
        self.bot.add_packet_handler(server_packets.PublicChannelMessage.id, self.handle_public_channel_message)

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS tower_victory (id INT NOT NULL PRIMARY KEY AUTO_INCREMENT, created_at INT NOT NULL, win_org_name VARCHAR(50) NOT NULL, "
                     "win_faction VARCHAR(10) NOT NULL, lose_org_name VARCHAR(50) NOT NULL, lose_faction VARCHAR(10) NOT NULL, attack_id INT)")
        self.db.exec("CREATE TABLE IF NOT EXISTS tower_attack (id INT NOT NULL PRIMARY KEY AUTO_INCREMENT, created_at INT NOT NULL, att_org_name VARCHAR(50) NOT NULL, "
                     "att_faction VARCHAR(10) NOT NULL, att_player VARCHAR(20) NOT NULL, att_level int, att_ai_level int, att_profession VARCHAR(15), def_org_name VARCHAR(50), "
                     "def_faction VARCHAR(10), playfield_id INT, site_number INT, x_coords INT, y_coords INT)")

    @command(command="lc", params=[], description="See a list of playfields containing land control tower sites", access_level="all")
    def lc_list_cmd(self, request):
        data = self.db.query("SELECT * FROM playfields WHERE id IN (SELECT DISTINCT playfield_id FROM tower_site) ORDER BY short_name")

        blob = ""
        for row in data:
            blob += "%s <highlight>%s<end>\n" % (self.text.make_chatcmd(row.long_name, "/tell <myname> lc %s" % row.short_name), row.short_name)

        return ChatBlob("Land Control Playfields", blob)

    @command(command="lc", params=[Any("playfield")], description="See a list of land control tower sites in a particular playfield", access_level="all")
    def lc_playfield_cmd(self, request, playfield_name):
        playfield = self.playfield_controller.get_playfield_by_name(playfield_name)
        if not playfield:
            return "Could not find playfield <highlight>%s<end>." % playfield_name

        data = self.db.query("SELECT t.*, p.short_name, p.long_name FROM tower_site t JOIN playfields p ON t.playfield_id = p.id WHERE t.playfield_id = ?", [playfield.id])

        blob = ""
        for row in data:
            blob += "<pagebreak>" + self.format_site_info(row) + "\n\n"

        return ChatBlob("Tower Sites in %s" % playfield.long_name, blob)

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
                self.event_service.fire_event(self.TOWER_VICTORY_EVENT, victory)
            else:
                # Unknown victory
                self.logger.warning("Unknown tower victory: " + str(packet))
        elif packet.channel_id == self.ALL_TOWERS_ID:
            attack = self.get_attack_event(packet)

            if attack:
                self.event_service.fire_event(self.TOWER_ATTACK_EVENT, attack)
            else:
                # Unknown attack
                self.logger.warning("Unknown tower attack: " + str(packet))

    def get_attack_event(self, packet: server_packets.PublicChannelMessage):
        attack = None
        if packet.extended_message:
            params = packet.extended_message.params
            if [packet.extended_message.category_id, packet.extended_message.instance_id] == self.ATTACK_1:
                attack = DictObject({
                    "attacker": {
                        "name": params[2],
                        "faction": params[0].capitalize(),
                        "org": params[1]
                    },
                    "defender": {
                        "faction": params[3].capitalize(),
                        "org": params[4]
                    },
                    "location": {
                        "playfield": {
                            "name": params[5]
                        },
                        "x_coord": params[6],
                        "y_coord": params[7]
                    }
                })
            elif [packet.extended_message.category_id, packet.extended_message.instance_id] == self.ATTACK_2:
                attack = DictObject({
                    "attacker": {
                        "name": "",
                        "faction": "",
                        "org": ""
                    },
                    "defender": {
                        "faction": params[0].capitalize(),
                        "org": params[1]
                    },
                    "location": {
                        "playfield": {
                            "name": params[2]
                        },
                        "x_coord": 0,
                        "y_coord": 0
                    }
                })
        else:
            match = self.ATTACK_3.match(packet.message)
            if match:
                attack = DictObject({
                    "attacker": {
                        "name": match.group(1),
                        "faction": "",
                        "org": ""
                    },
                    "defender": {
                        "faction": match.group(2).capitalize(),
                        "org": match.group(3)
                    },
                    "location": {
                        "playfield": {
                            "name": match.group(4)
                        },
                        "x_coord": match.group(5),
                        "y_coord": match.group(6)
                    }
                })

        return attack

    def get_victory_event(self, packet: server_packets.PublicChannelMessage):
        victory = None

        match = self.VICTORY_1.match(packet.message)
        if match:
            victory = DictObject({
                "attacker": {
                    "faction": match.group(1).capitalize(),
                    "org": match.group(2)
                },
                "defender": {
                    "faction": match.group(3).capitalize(),
                    "org": match.group(4)
                },
                "location": {
                    "playfield": {
                        "name": match.group(5)
                    }
                }
            })

        return victory
