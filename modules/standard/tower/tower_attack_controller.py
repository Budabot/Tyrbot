from core.chat_blob import ChatBlob
from core.command_param_types import Const, Int, NamedParameters
from core.decorators import instance, command, event
from core.logger import Logger
from core.setting_types import BooleanSettingType
from modules.standard.tower.tower_controller import TowerController
import time


@instance()
class TowerAttackController:
    MESSAGE_SOURCE = "tower_attacks"

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
        self.public_channel_service = registry.get_instance("public_channel_service")
        self.message_hub_service = registry.get_instance("message_hub_service")

    def pre_start(self):
        self.message_hub_service.register_message_source(self.MESSAGE_SOURCE)

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS tower_attacker (id INT PRIMARY KEY AUTO_INCREMENT, att_org_name VARCHAR(50) NOT NULL, att_faction VARCHAR(10) NOT NULL, "
                     "att_char_id INT, att_char_name VARCHAR(20) NOT NULL, att_level INT NOT NULL, att_ai_level INT NOT NULL, att_profession VARCHAR(15) NOT NULL, "
                     "x_coord INT NOT NULL, y_coord INT NOT NULL, is_victory SMALLINT NOT NULL, "
                     "tower_battle_id INT NOT NULL, created_at INT NOT NULL)")
        self.db.exec("CREATE TABLE IF NOT EXISTS tower_battle (id INT PRIMARY KEY AUTO_INCREMENT, playfield_id INT NOT NULL, site_number INT NOT NULL, "
                     "def_org_name VARCHAR(50) NOT NULL, def_faction VARCHAR(10) NOT NULL, is_finished INT NOT NULL, battle_type VARCHAR(20) NOT NULL, last_updated INT NOT NULL)")

        self.command_alias_service.add_alias("victory", "attacks")

        self.setting_service.register(self.module_name, "show_tower_attack_messages", True, BooleanSettingType(), "Show tower attack messages")

    @command(command="attacks", params=[NamedParameters(["page"])], access_level="all",
             description="Show recent tower attacks and victories")
    def attacks_cmd(self, request, named_params):
        page_number = int(named_params.page or "1")

        page_size = 10
        offset = (page_number - 1) * page_size

        sql = """SELECT b.*, p.long_name, p.short_name 
            FROM tower_battle b LEFT JOIN playfields p ON b.playfield_id = p.id 
            ORDER bY b.last_updated DESC LIMIT ?, ?"""
        data = self.db.query(sql, [offset, page_size])

        t = int(time.time())

        blob = self.check_for_all_towers_channel()
        blob += self.text.get_paging_links(f"attacks", page_number, page_size == len(data))
        blob += "\n\n"
        for row in data:
            blob += "\n<pagebreak>"
            blob += self.format_battle_info(row, t)
            blob += self.text.make_tellcmd("More Info", "attacks battle %d" % row.id) + "\n"
            blob += "<header2>Attackers:</header2>\n"
            sql2 = """SELECT a.*, COALESCE(a.att_level, 0) AS att_level, COALESCE(a.att_ai_level, 0) AS att_ai_level
                FROM tower_attacker a
                WHERE a.tower_battle_id = ?
                ORDER BY created_at DESC"""
            data2 = self.db.query(sql2, [row.id])
            for row2 in data2:
                blob += "<tab>" + self.format_attacker(row2) + "\n"
            if not data2:
                blob += "<tab>Unknown attacker\n"

        return ChatBlob("Tower Attacks", blob)

    @command(command="attacks", params=[Const("battle"), Int("battle_id")], access_level="all",
             description="Show battle info for a specific battle")
    def attacks_battle_cmd(self, request, _, battle_id):
        battle = self.get_battle(battle_id)
        if not battle:
            return "Could not find battle with ID <highlight>%d</highlight>." % battle_id

        blob = self.check_for_all_towers_channel() + self.get_battle_blob(battle)

        return ChatBlob("Battle Info %d" % battle_id, blob)

    @event(event_type=TowerController.TOWER_ATTACK_EVENT, description="Record tower attacks", is_hidden=True)
    def tower_attack_event(self, event_type, event_data):
        t = int(time.time())
        site_number = self.find_closest_site_number(event_data.location.playfield.id, event_data.location.x_coord, event_data.location.y_coord)

        attacker = event_data.attacker or {}
        defender = event_data.defender
        location = event_data.location

        battle = self.find_or_create_battle(event_data.location.playfield.id, site_number, defender.org_name, defender.faction, "attack", t)

        self.db.exec("INSERT INTO tower_attacker (att_org_name, att_faction, att_char_id, att_char_name, att_level, att_ai_level, att_profession, "
                     "x_coord, y_coord, is_victory, tower_battle_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     [attacker.get("org_name", ""), attacker.get("faction", ""), attacker.get("char_id", 0), attacker.get("name", ""), attacker.get("level", 0),
                      attacker.get("ai_level", 0), attacker.get("profession", ""), location.x_coord, location.y_coord, 0, battle.id, t])
        attacker_id = self.db.last_insert_id()

        if self.setting_service.get("show_tower_attack_messages").get_value():
            attacker_row = self.db.query_single("SELECT * FROM tower_attacker WHERE id = ?", [attacker_id])
            more_info = self.text.paginate_single(ChatBlob("More Info", self.text.make_tellcmd("More Info", f"attacks battle {battle.id}")), self.bot.get_primary_conn())
            msg = "%s attacked %s [%s] at %s %s %s" % (self.format_attacker(attacker_row), defender.org_name, self.text.get_formatted_faction(defender.faction),
                                                       location.playfield.get("short_name", location.playfield.get("long_name")), site_number or "?", more_info)
            self.message_hub_service.send_message(self.MESSAGE_SOURCE, None, None, msg)

    @event(event_type=TowerController.TOWER_VICTORY_EVENT, description="Record tower victories", is_hidden=True)
    def tower_victory_event(self, event_type, event_data):
        t = int(time.time())

        if event_data.type == "attack":
            last_updated = t - (6 * 3600)
            row = self.get_last_attack(
                event_data.winner.faction, event_data.winner.org_name, event_data.loser.faction, event_data.loser.org_name,
                event_data.location.playfield.id, last_updated)

            if not row:
                site_number = 0
                is_finished = 1
                is_victory = 1
                self.db.exec("INSERT INTO tower_battle (playfield_id, site_number, def_org_name, def_faction, is_finished, battle_type, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             [event_data.location.playfield.id, site_number, event_data.loser.org_name, event_data.loser.faction, is_finished, event_data.type, t])
                battle_id = self.db.last_insert_id()

                attacker = event_data.winner or {}
                self.db.exec("INSERT INTO tower_attacker (att_org_name, att_faction, att_char_id, att_char_name, att_level, att_ai_level, att_profession, "
                             "x_coord, y_coord, is_victory, tower_battle_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             [attacker.get("org_name", ""), attacker.get("faction", ""), attacker.get("char_id", 0), attacker.get("name", ""), attacker.get("level", 0),
                              attacker.get("ai_level", 0), attacker.get("profession", ""), 0, 0, is_victory, battle_id, t])
            else:
                is_victory = 1
                self.db.exec("UPDATE tower_attacker SET is_victory = ? WHERE id = ?", [is_victory, row.attack_id])

                is_finished = 1
                self.db.exec("UPDATE tower_battle SET is_finished = ?, last_updated = ? WHERE id = ?", [is_finished, t, row.battle_id])
        elif event_data.type == "terminated":
            site_number = 0
            is_finished = 1
            self.db.exec("INSERT INTO tower_battle (playfield_id, site_number, def_org_name, def_faction, is_finished, battle_type, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         [event_data.location.playfield.id, site_number, event_data.loser.org_name, event_data.loser.faction, is_finished, event_data.type, t])
        else:
            raise Exception("Unknown victory event type: '%s'" % event_data.type)

    @event(event_type=TowerController.TOWER_VICTORY_EVENT, description="Remove scout info for tower sites that are destroyed", is_hidden=True, is_enabled=False)
    def tower_scout_info_cleanup_event(self, event_type, event_data):
        # TODO use site_number when available
        self.db.exec("DELETE FROM scout_info WHERE playfield_id = ? AND faction = ? AND org_name = ?",
                     [event_data.location.playfield.id, event_data.loser.faction, event_data.loser.org_name])

    def format_attacker(self, row):
        level = ("%d/<green>%d</green>" % (row.att_level, row.att_ai_level)) if row.att_ai_level > 0 else "%d" % row.att_level
        org = row.att_org_name + " " if row.att_org_name else ""
        victor = " - <notice>Winner!</notice>" if row.is_victory else ""
        return "%s (%s %s) %s[%s]%s" % (row.att_char_name or "Unknown attacker", level, row.att_profession, org, self.text.get_formatted_faction(row.att_faction), victor)

    def find_closest_site_number(self, playfield_id, x_coord, y_coord):
        sql = "SELECT site_number FROM tower_site_bounds " \
              "WHERE playfield_id = ? AND x_coord1 <= ? AND x_coord2 >= ? AND y_coord1 >= ? AND y_coord2 <= ?"
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
                a.id AS attack_id
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
        blob += "Site: <highlight>%s %s</highlight>\n" % (row.short_name, row.site_number or "?")
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
        if TowerController.ALL_TOWERS_ID not in self.bot.get_primary_conn().channels:
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
            blob += "\n"

        return blob

    def get_battle(self, battle_id):
        return self.db.query_single("SELECT b.*, p.short_name, p.long_name, t.site_name, t.x_coord, t.y_coord, t.min_ql, t.max_ql "
                                    "FROM tower_battle b "
                                    "LEFT JOIN playfields p ON p.id = b.playfield_id "
                                    "LEFT JOIN tower_site t ON b.playfield_id = t.playfield_id AND b.site_number = t.site_number "
                                    "WHERE b.id = ?", [battle_id])
