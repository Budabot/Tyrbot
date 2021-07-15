import pytz
import re
import requests
import time
from requests import ReadTimeout
from datetime import datetime

from core.chat_blob import ChatBlob
from core.command_param_types import Any, Int, Const, Options
from core.conn import Conn
from core.db import DB
from core.decorators import instance, command, event
from core.dict_object import DictObject
from core.event_service import EventService
from core.feature_flags import FeatureFlags
from core.logger import Logger
from core.aochat import server_packets
from core.lookup.pork_service import PorkService
from core.public_channel_service import PublicChannelService
from core.text import Text
from core.tyrbot import Tyrbot
from modules.standard.helpbot.playfield_controller import PlayfieldController


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
        self.util = registry.get_instance("util")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.event_service: EventService = registry.get_instance("event_service")
        self.pork_service: PorkService = registry.get_instance("pork_service")
        self.playfield_controller: PlayfieldController = registry.get_instance("playfield_controller")
        self.public_channel_service: PublicChannelService = registry.get_instance("public_channel_service")

    def pre_start(self):
        self.event_service.register_event_type(self.TOWER_ATTACK_EVENT)
        self.event_service.register_event_type(self.TOWER_VICTORY_EVENT)
        self.bot.register_packet_handler(server_packets.PublicChannelMessage.id, self.handle_public_channel_message)

        self.db.load_sql_file(self.module_dir + "/" + "tower_site.sql")
        self.db.load_sql_file(self.module_dir + "/" + "tower_site_bounds.sql")
        self.db.load_sql_file(self.module_dir + "/" + "scout_info.sql")

    def start(self):
        self.command_alias_service.add_alias("hot", "lc open")

    @command(command="lc", params=[], access_level="all",
             description="See a list of playfields containing land control tower sites")
    def lc_list_cmd(self, request):
        data = self.db.query("SELECT id, long_name, short_name FROM playfields WHERE id IN (SELECT DISTINCT playfield_id FROM tower_site) ORDER BY short_name")

        blob = ""
        for row in data:
            blob += "[%d] %s <highlight>%s</highlight>\n" % (row.id, self.text.make_tellcmd(row.long_name, "lc %s" % row.short_name), row.short_name)

        blob += "\n" + self.get_lc_blob_footer()

        return ChatBlob("Land Control Playfields (%d)" % len(data), blob)

    if FeatureFlags.USE_TOWER_API:
        @command(command="lc", params=[Const("org"), Any("org", is_optional=True)], access_level="all",
                 description="See a list of land control tower sites by org")
        def lc_org_cmd(self, request, _, org):
            params = {"enabled": "true"}
            if not org:
                org = str(request.conn.org_id)
                if not org:
                    return "Bot does not belong to an org so an org name or org id must be specified."

            if org.isdigit():
                params["org_id"] = org
            else:
                params["org_name"] = "%" + org + "%"
            data = self.lookup_tower_info(params).results

            if not data:
                return "Could not find tower info for org <highlight>%s</highlight>." % org

            blob = ""
            current_day_time = int(time.time()) % 86400
            for row in data:
                blob += "<pagebreak>" + self.format_site_info(row, current_day_time) + "\n\n"

            blob += self.get_lc_blob_footer()

            title = "Tower Info: %s (%d)" % (org, len(data))

            return ChatBlob(title, blob)

        @command(command="lc", params=[Const("unplanted")],
                 access_level="all", description="See a list of land control tower sites that are not currently planted")
        def lc_unplanted_cmd(self, request, _):
            params = {"enabled": "true", "planted": "false"}

            data = self.lookup_tower_info(params).results

            if not data:
                return "There are no tower sites matching your criteria."

            blob = ""
            for row in data:
                blob += "<pagebreak>" + self.format_site_info(row, None) + "\n\n"

            blob += self.get_lc_blob_footer()

            title = "Tower Info: Unplanted"
            title += " (%d)" % len(data)

            return ChatBlob(title, blob)

        @command(command="lc", params=[Options(["open", "closed", "all"]),
                                       Options(["omni", "clan", "neutral", "all"], is_optional=True),
                                       Int("min_ql", is_optional=True),
                                       Int("max_ql", is_optional=True)],
                 access_level="all", description="See a list of land control tower sites by QL, faction, and open status")
        def lc_search_cmd(self, request, site_status, faction, min_ql, max_ql):
            t = int(time.time())
            current_day_time = t % 86400
            min_ql = min_ql or 1
            max_ql = max_ql or 300

            params = {"enabled": "true", "min_ql": min_ql, "max_ql": max_ql}

            if faction:
                params["faction"] = faction

            if site_status.lower() == "open":
                params["min_close_time"] = current_day_time
                params["max_close_time"] = self.day_time(current_day_time + (3600 * 6))
            elif site_status.lower() == "closed":
                params["min_close_time"] = self.day_time(current_day_time + (3600 * 6))
                params["max_close_time"] = current_day_time

            data = self.lookup_tower_info(params).results

            if not data:
                return "There are no tower sites matching your criteria."

            blob = ""
            for row in data:
                blob += "<pagebreak>" + self.format_site_info(row, current_day_time) + "\n\n"

            blob += self.get_lc_blob_footer()

            title = "Tower Info: %s" % site_status.capitalize()
            title += " QL %d - %d" % (min_ql, max_ql)
            if faction:
                title += " [%s]" % faction.capitalize()
            title += " (%d)" % len(data)

            return ChatBlob(title, blob)

    @command(command="lc", params=[Any("playfield"), Int("site_number", is_optional=True)], access_level="all",
             description="See a list of land control tower sites in a particular playfield")
    def lc_playfield_cmd(self, request, playfield_name, site_number):
        playfield = self.playfield_controller.get_playfield_by_name(playfield_name)
        if not playfield:
            return "Could not find playfield <highlight>%s</highlight>." % playfield_name

        data = self.get_tower_site_info(playfield.id, site_number)

        if not data:
            if site_number:
                return "Could not find tower info for <highlight>%s %d</highlight>." % (playfield.long_name, site_number)
            else:
                return "Could not find tower info for <highlight>%s</highlight>." % playfield.long_name

        blob = ""
        current_day_time = int(time.time()) % 86400
        for row in data:
            blob += "<pagebreak>" + self.format_site_info(row, current_day_time) + "\n\n"

        blob += self.get_lc_blob_footer()

        if site_number:
            title = "Tower Info: %s %d" % (playfield.long_name, site_number)
        else:
            title = "Tower Info: %s (%d)" % (playfield.long_name, len(data))

        return ChatBlob(title, blob)

    @event(event_type="connect", description="Check if All Towers channel is available", is_hidden=True)
    def handle_connect_event(self, event_type, event_data):
        conn = self.bot.get_primary_conn()
        if conn.org_id and TowerController.ALL_TOWERS_ID not in conn.channels:
            self.logger.warning("The primary bot is a member of an org but does not have access to 'All Towers' channel and therefore will not be able to record tower attacks")

    def format_site_info(self, row, current_day_time):
        blob = "<highlight>%s %d</highlight> (QL %d-%d)\n" % (row.playfield_short_name, row.site_number, row.min_ql, row.max_ql)

        if row.get("org_name"):
            t = int(time.time())
            value = datetime.fromtimestamp(row.close_time, tz=pytz.UTC)
            current_status_time = row.close_time - current_day_time
            if current_status_time < 0:
                current_status_time += 86400

            if current_status_time <= 3600:
                status = "<red>5%%</red> (closes in %s)" % self.util.time_to_readable(current_status_time)
            elif current_status_time <= (3600 * 6):
                status = "<orange>25%%</green> (closes in %s)" % self.util.time_to_readable(current_status_time)
            else:
                status = "<green>75%%</green> (opens in %s)" % self.util.time_to_readable(current_status_time - (3600 * 6))

            blob += "%s (%d) [%s] QL %d <highlight>%s</highlight> %s\n" % (
                row.org_name,
                row.org_id,
                self.text.get_formatted_faction(row.faction),
                row.ql,
                self.util.time_to_readable(t - row.created_at),
                self.text.make_chatcmd("%dx%d" % (row.x_coord, row.y_coord), "/waypoint %d %d %d" % (row.x_coord, row.y_coord, row.playfield_id)))
            blob += "Close Time: <highlight>%s</highlight> %s\n" % (value.strftime("%H:%M:%S %Z"), status)
        else:
            blob += "%s\n" % self.text.make_chatcmd("%dx%d" % (row.x_coord, row.y_coord), "/waypoint %d %d %d" % (row.x_coord, row.y_coord, row.playfield_id))
            if not row.enabled:
                blob += "<red>Disabled</red>\n"

        return blob

    def get_tower_site_info(self, playfield_id, site_number):
        if FeatureFlags.USE_TOWER_API:
            params = {"playfield_id": playfield_id}
            if site_number:
                params["site_number"] = site_number

            data = self.lookup_tower_info(params).results
        else:
            if site_number:
                data = self.db.query("SELECT t.*, p.short_name AS playfield_short_name, p.long_name AS playfield_long_name "
                                     "FROM tower_site t JOIN playfields p ON t.playfield_id = p.id WHERE t.playfield_id = ? AND site_number = ?",
                                     [playfield_id, site_number])
            else:
                data = self.db.query("SELECT t.*, p.short_name AS playfield_short_name, p.long_name AS playfield_long_name "
                                     "FROM tower_site t JOIN playfields p ON t.playfield_id = p.id WHERE t.playfield_id = ?",
                                     [playfield_id])

        return data

    def handle_public_channel_message(self, conn: Conn, packet: server_packets.PublicChannelMessage):
        # only listen to tower packets from first bot, to avoid triggering multiple times
        if conn != self.bot.get_primary_conn():
            return

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
                char_info = self.pork_service.get_character_info(name)
                attack.attacker = char_info or DictObject()
                attack.attacker.name = name
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

    def lookup_tower_info(self, params):
        url = "https://tower-api.jkbff.com/api/towers"

        try:
            r = requests.get(url, params, headers={"User-Agent": f"Tyrbot {self.bot.version}"}, timeout=5)
            result = DictObject(r.json())
        except ReadTimeout:
            self.logger.warning("Timeout while requesting '%s'" % url)
            result = None
        except Exception as e:
            self.logger.error("Error requesting history for url '%s'" % url, e)
            result = None

        return result

    def day_time(self, day_t):
        if day_t > 86400:
            day_t -= 86400
        elif day_t < 0:
            day_t += 86400
        return day_t

    def get_lc_blob_footer(self):
        return "Thanks to Draex and Unk for providing the tower information. And a special thanks to Trey."
