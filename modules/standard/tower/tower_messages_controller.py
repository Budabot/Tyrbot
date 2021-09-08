import re

from core.aochat import server_packets
from core.chat_blob import ChatBlob
from core.command_param_types import Const, Int, NamedParameters, Any
from core.conn import Conn
from core.decorators import instance, command, event
from core.dict_object import DictObject
from core.logger import Logger
import time

from modules.standard.helpbot.playfield_controller import PlayfieldController


@instance()
class TowerMessagesController:
    MESSAGE_SOURCE = "tower_attacks"

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
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.setting_service = registry.get_instance("setting_service")
        self.event_service = registry.get_instance("event_service")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.pork_service = registry.get_instance("pork_service")
        self.public_channel_service = registry.get_instance("public_channel_service")
        self.message_hub_service = registry.get_instance("message_hub_service")
        self.playfield_controller: PlayfieldController = registry.get_instance("playfield_controller")

    def pre_start(self):
        self.message_hub_service.register_message_source(self.MESSAGE_SOURCE)

        self.event_service.register_event_type(self.TOWER_ATTACK_EVENT)
        self.event_service.register_event_type(self.TOWER_VICTORY_EVENT)
        self.bot.register_packet_handler(server_packets.PublicChannelMessage.id, self.handle_public_channel_message)

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS tower_attacker (id INT PRIMARY KEY AUTO_INCREMENT, att_org_name VARCHAR(50) NOT NULL, att_faction VARCHAR(10) NOT NULL, "
                     "att_char_id INT, att_char_name VARCHAR(20) NOT NULL, att_level INT NOT NULL, att_ai_level INT NOT NULL, att_profession VARCHAR(15) NOT NULL, "
                     "x_coord INT NOT NULL, y_coord INT NOT NULL, is_victory SMALLINT NOT NULL, "
                     "tower_battle_id INT NOT NULL, created_at INT NOT NULL)")
        self.db.exec("CREATE TABLE IF NOT EXISTS tower_battle (id INT PRIMARY KEY AUTO_INCREMENT, playfield_id INT NOT NULL, site_number INT NOT NULL, "
                     "def_org_name VARCHAR(50) NOT NULL, def_faction VARCHAR(10) NOT NULL, is_finished INT NOT NULL, battle_type VARCHAR(20) NOT NULL, last_updated INT NOT NULL)")

        self.command_alias_service.add_alias("victory", "attacks")

    @command(command="attacks", params=[Const("battle"), Int("battle_id")], access_level="all",
             description="Show battle info for a specific battle")
    def attacks_battle_cmd(self, request, _, battle_id):
        battle = self.get_battle(battle_id)
        if not battle:
            return "Could not find battle with ID <highlight>%d</highlight>." % battle_id

        blob = self.check_for_all_towers_channel() + self.get_battle_blob(battle)

        return ChatBlob("Battle Info %d" % battle_id, blob)

    @command(command="attacks", params=[Any("playfield", is_optional=True, allowed_chars="[a-z0-9 ]"),
                                        Int("site_number", is_optional=True),
                                        NamedParameters(["page"])],
             access_level="all", description="Show recent tower attacks and victories")
    def attacks_cmd(self, request, playfield_name, site_number, named_params):
        playfield = None
        if playfield_name:
            playfield = self.playfield_controller.get_playfield_by_name_or_id(playfield_name)
            if not playfield:
                return f"Could not find playfield <highlight>{playfield_name}</highlight>."

        page_number = int(named_params.page or "1")

        page_size = 10
        offset = (page_number - 1) * page_size

        sql = "SELECT b.*, p.long_name, p.short_name FROM tower_battle b LEFT JOIN playfields p ON b.playfield_id = p.id"
        params = []

        if playfield:
            sql += " WHERE b.playfield_id = ?"
            params.append(playfield.id)
            if site_number:
                sql += " AND b.site_number = ?"
                params.append(site_number)

        sql += " ORDER BY b.last_updated DESC LIMIT ?, ?"
        params.append(offset)
        params.append(page_size)

        data = self.db.query(sql, params)

        t = int(time.time())

        command_str = "attacks"
        if playfield_name:
            command_str += " " + playfield_name
            if site_number:
                command_str += " " + str(site_number)

        blob = self.check_for_all_towers_channel()
        blob += self.text.get_paging_links(command_str, page_number, page_size == len(data))
        blob += "\n\n"
        for row in data:
            blob += "\n<pagebreak>"
            blob += self.format_battle_info(row, t)
            blob += "<header2>Attackers:</header2>\n"
            sql2 = """SELECT a.*, COALESCE(a.att_level, 0) AS att_level, COALESCE(a.att_ai_level, 0) AS att_ai_level
                    FROM tower_attacker a
                    WHERE a.tower_battle_id = ?
                    ORDER BY created_at DESC"""
            data2 = self.db.query(sql2, [row.id])
            for row2 in data2:
                blob += "<tab>" + self.format_attacker(row2)
                if row2.is_victory:
                    blob += " - <notice>Winner!</notice>"
                blob += "\n"
            if not data2:
                blob += "<tab>Unknown attacker\n"

        title = "Tower Attacks"
        if playfield:
            title += f" ({playfield.long_name}"
            if site_number:
                title += " " + str(site_number)
            title += ")"

        return ChatBlob(title, blob)

    @event(event_type="connect", description="Check if All Towers channel is available", is_hidden=True)
    def handle_connect_event(self, event_type, event_data):
        conn = self.bot.get_primary_conn()
        if conn.org_id and self.ALL_TOWERS_ID not in conn.channels:
            self.logger.warning("The primary bot is a member of an org but does not have access to 'All Towers' channel and therefore will not be able to record tower attacks")

    @event(event_type=TOWER_VICTORY_EVENT, description="Remove scout info for tower sites that are destroyed", is_hidden=True, is_enabled=False)
    def tower_scout_info_cleanup_event(self, event_type, event_data):
        if event_data.location.site_number:
            self.db.exec("DELETE FROM scout_info WHERE playfield_id = ? AND site_number = ?",
                         [event_data.location.playfield.id, event_data.location.site_number])
        else:
            self.db.exec("DELETE FROM scout_info WHERE playfield_id = ? AND faction = ? AND org_name = ?",
                         [event_data.location.playfield.id, event_data.loser.faction, event_data.loser.org_name])

    def handle_public_channel_message(self, conn: Conn, packet: server_packets.PublicChannelMessage):
        # only listen to tower packets from first bot, to avoid triggering multiple times
        if conn != self.bot.get_primary_conn():
            return

        if packet.channel_id == self.TOWER_BATTLE_OUTCOME_ID:
            victory = self.get_victory_event(packet)
            if victory:
                self.fire_victory_event(victory)
        elif packet.channel_id == self.ALL_TOWERS_ID:
            attack = self.get_attack_event(packet)
            if attack:
                self.fire_attack_event(attack)

    def fire_victory_event(self, obj):
        # self.logger.debug("tower victory packet: %s" % str(packet))

        # lookup playfield
        playfield_name = obj.location.playfield.long_name
        obj.location.playfield = self.playfield_controller.get_playfield_by_name(playfield_name) or DictObject()
        obj.location.playfield.long_name = playfield_name

        t = int(time.time())
        is_victory = 1
        is_finished = 1

        if obj.type == "attack":
            # get battle id and site_number
            last_updated = t - (6 * 3600)
            row = self.get_last_attack(
                obj.winner.faction, obj.winner.org_name, obj.loser.faction, obj.loser.org_name,
                obj.location.playfield.id, last_updated)

            if row:
                obj.battle_id = row.battle_id
                obj.location.site_number = row.site_number

                self.db.exec("UPDATE tower_attacker SET is_victory = ? WHERE id = ?", [is_victory, row.attack_id])
                self.db.exec("UPDATE tower_battle SET is_finished = ?, last_updated = ? WHERE id = ?", [is_finished, t, row.battle_id])
            else:
                obj.location.site_number = 0
                self.db.exec("INSERT INTO tower_battle (playfield_id, site_number, def_org_name, def_faction, is_finished, battle_type, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             [obj.location.playfield.id, obj.location.site_number, obj.loser.org_name, obj.loser.faction, is_finished, obj.type, t])
                obj.battle_id = self.db.last_insert_id()

                attacker = obj.winner or {}
                self.db.exec("INSERT INTO tower_attacker (att_org_name, att_faction, att_char_id, att_char_name, att_level, att_ai_level, att_profession, "
                             "x_coord, y_coord, is_victory, tower_battle_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             [attacker.get("org_name", ""), attacker.get("faction", ""), attacker.get("char_id", 0), attacker.get("name", ""), attacker.get("level", 0),
                              attacker.get("ai_level", 0), attacker.get("profession", ""), 0, 0, is_victory, obj.battle_id, t])

        elif obj.type == "terminated":
            obj.location.site_number = 0
            self.db.exec("INSERT INTO tower_battle (playfield_id, site_number, def_org_name, def_faction, is_finished, battle_type, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         [obj.location.playfield.id, obj.location.site_number, obj.loser.org_name, obj.loser.faction, is_finished, obj.type, t])
        else:
            raise Exception("Unknown victory event type: '%s'" % obj.type)

        self.event_service.fire_event(self.TOWER_VICTORY_EVENT, obj)

    def fire_attack_event(self, obj):
        # self.logger.debug("tower attack packet: %s" % str(packet))

        # lookup playfield
        playfield_name = obj.location.playfield.long_name
        obj.location.playfield = self.playfield_controller.get_playfield_by_name(playfield_name) or DictObject()
        obj.location.playfield.long_name = playfield_name

        # lookup attacker
        name = obj.attacker.name
        faction = obj.attacker.faction
        org_name = obj.attacker.org_name
        char_info = self.pork_service.get_character_info(name)
        obj.attacker = char_info or DictObject()
        obj.attacker.name = name
        obj.attacker.faction = faction or obj.attacker.get("faction", "Unknown")
        obj.attacker.org_name = org_name

        obj.location.site_number = self.find_closest_site_number(obj.location.playfield.id, obj.location.x_coord, obj.location.y_coord)

        attacker = obj.attacker or {}
        defender = obj.defender
        location = obj.location

        t = int(time.time())
        battle = self.find_or_create_battle(obj.location.playfield.id, obj.location.site_number, defender.org_name, defender.faction, "attack", t)

        self.db.exec("INSERT INTO tower_attacker (att_org_name, att_faction, att_char_id, att_char_name, att_level, att_ai_level, att_profession, "
                     "x_coord, y_coord, is_victory, tower_battle_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     [attacker.get("org_name", ""), attacker.get("faction", ""), attacker.get("char_id", 0), attacker.get("name", ""), attacker.get("level", 0),
                      attacker.get("ai_level", 0), attacker.get("profession", ""), location.x_coord, location.y_coord, 0, battle.id, t])
        attacker_id = self.db.last_insert_id()

        attacker_row = self.db.query_single("SELECT * FROM tower_attacker WHERE id = ?", [attacker_id])
        more_info = self.text.paginate_single(ChatBlob("More Info", self.text.make_tellcmd("More Info", f"attacks battle {battle.id}")), self.bot.get_primary_conn())
        msg = "%s attacked %s [%s] at %s %s %s" % (self.format_attacker(attacker_row), defender.org_name, self.text.get_formatted_faction(defender.faction),
                                                   location.playfield.get("short_name", location.playfield.get("long_name")), obj.location.site_number or "?", more_info)
        self.message_hub_service.send_message(self.MESSAGE_SOURCE, None, None, msg)

        self.event_service.fire_event(self.TOWER_ATTACK_EVENT, obj)

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

    def format_attacker(self, row):
        level = ("%d/<green>%d</green>" % (row.att_level, row.att_ai_level)) if row.att_ai_level > 0 else "%d" % row.att_level
        org = row.att_org_name + " " if row.att_org_name else ""
        return "%s (%s %s) %s[%s]" % (row.att_char_name or "Unknown attacker", level, row.att_profession, org, self.text.get_formatted_faction(row.att_faction))

    def find_closest_site_number(self, playfield_id, x_coord, y_coord):
        sql = "SELECT site_number FROM tower_site_bounds " \
              "WHERE playfield_id = ? AND x_coord1 <= ? AND x_coord2 >= ? AND y_coord1 >= ? AND y_coord2 <= ? " \
              "LIMIT 1"
        row = self.db.query_single(sql, [playfield_id, x_coord, x_coord, y_coord, y_coord])
        if row:
            return row.site_number

        sql = """
            SELECT
                site_number,
                ((x_distance * x_distance) + (y_distance * y_distance)) radius
            FROM
                (SELECT
                    playfield_id,
                    site_number,
                    min_ql,
                    max_ql,
                    x_coord,
                    y_coord,
                    site_name,
                    (x_coord - ?) as x_distance,
                    (y_coord - ?) as y_distance
                FROM
                    tower_site
                WHERE
                    playfield_id = ?) t
            ORDER BY
                radius ASC
            LIMIT 1"""

        row = self.db.query_single(sql, [x_coord, y_coord, playfield_id])
        if row:
            return row.site_number
        else:
            return 0

    def find_or_create_battle(self, playfield_id, site_number, org_name, faction, battle_type, t):
        last_updated = t - (8 * 3600)
        is_finished = 0

        sql = """
            SELECT
                id
            FROM
                tower_battle
            WHERE
                playfield_id = ?
                AND site_number = ?
                AND is_finished = ?
                AND def_org_name = ?
                AND def_faction = ?
                AND last_updated >= ?
        """

        battle = self.db.query_single(sql, [playfield_id, site_number, is_finished, org_name, faction, last_updated])

        if battle:
            self.db.exec("UPDATE tower_battle SET last_updated = ? WHERE id = ?", [t, battle.id])
            battle_id = battle.id
        else:
            self.db.exec("INSERT INTO tower_battle (playfield_id, site_number, def_org_name, def_faction, is_finished, battle_type, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         [playfield_id, site_number, org_name, faction, is_finished, battle_type, t])
            battle_id = self.db.last_insert_id()

        return self.get_battle(battle_id)

    def get_last_attack(self, att_faction, att_org_name, def_faction, def_org_name, playfield_id, last_updated):
        is_finished = 0

        sql = """
            SELECT
                b.id AS battle_id,
                a.id AS attack_id,
                b.site_number
            FROM
                tower_battle b
                JOIN tower_attacker a ON
                    a.tower_battle_id = b.id 
            WHERE
                a.att_faction = ?
                AND a.att_org_name = ?
                AND b.def_faction = ?
                AND b.def_org_name = ?
                AND b.playfield_id = ?
                AND b.is_finished = ?
                AND b.last_updated >= ?
            ORDER BY
                last_updated DESC
            LIMIT 1"""

        return self.db.query_single(sql, [att_faction, att_org_name, def_faction, def_org_name, playfield_id, is_finished, last_updated])

    def format_battle_info(self, row, t, verbose=False):
        blob = ""
        defeated = " - <notice>Defeated!</notice>" if row.is_finished else ""
        blob += "Site: <highlight>%s %s</highlight> " % (row.short_name, row.site_number or "?")
        if not verbose:
            blob += self.text.make_tellcmd("More Info", "attacks battle %d" % row.id)
        blob += "\n"
        if verbose:
            if row.site_number:
                blob += f"Long name: <highlight>{row.site_name}, {row.long_name}</highlight>\n"
                blob += f"Level range: <highlight>{row.min_ql}-{row.max_ql}</highlight>\n"
                blob += "Coordinates: %s\n" % self.text.make_chatcmd(f"{row.x_coord}x{row.y_coord}", f"/waypoint {row.x_coord} {row.y_coord} {row.playfield_id}")
            else:
                blob += f"Long name: Unknown\n"
                blob += f"Level range: Unknown\n"
                blob += "Coordinates: Unknown\n"
        blob += f"Defender: %s [%s]%s\n" % (row.def_org_name, self.text.get_formatted_faction(row.def_faction), defeated)
        blob += "Last Activity: %s\n" % self.format_timestamp(row.last_updated, t)
        return blob

    def format_timestamp(self, t, current_t):
        return "<highlight>%s</highlight> (%s ago)" % (self.util.format_datetime(t), self.util.time_to_readable(current_t - t))

    def get_chat_command(self, page):
        return "/tell <myname> attacks --page=%d" % page

    def check_for_all_towers_channel(self):
        if self.ALL_TOWERS_ID not in self.bot.get_primary_conn().channels:
            return "Notice: The primary bot must belong to an org and be promoted to a rank that is high enough to have the All Towers channel (e.g., Squad Commander) in order for the <symbol>attacks command to work correctly.\n\n"
        else:
            return ""

    def get_battle_blob(self, battle):
        t = int(time.time())

        attackers = self.db.query("SELECT * FROM tower_attacker WHERE tower_battle_id = ? ORDER BY created_at DESC", [battle.id])

        first_activity = attackers[-1].created_at if len(attackers) > 0 else battle.last_updated

        blob = ""
        blob += self.format_battle_info(battle, t, verbose=True)
        blob += "Duration: <highlight>%s</highlight>\n\n" % self.util.time_to_readable(battle.last_updated - first_activity)
        blob += "<header2>Attackers:</header2>\n"

        for row in attackers:
            blob += "<tab>" + self.format_attacker(row)
            blob += " " + self.format_timestamp(row.created_at, t)
            if row.is_victory:
                blob += " - <notice>Winner!</notice>"
            blob += "\n"

        return blob

    def get_battle(self, battle_id):
        return self.db.query_single("SELECT b.*, p.short_name, p.long_name, t.site_name, t.x_coord, t.y_coord, t.min_ql, t.max_ql "
                                    "FROM tower_battle b "
                                    "LEFT JOIN playfields p ON p.id = b.playfield_id "
                                    "LEFT JOIN tower_site t ON b.playfield_id = t.playfield_id AND b.site_number = t.site_number "
                                    "WHERE b.id = ?", [battle_id])
