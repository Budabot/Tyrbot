from core.chat_blob import ChatBlob
from core.command_param_types import Const, Int, NamedParameters
from core.decorators import instance, command, event
from core.dict_object import DictObject
from core.logger import Logger
from modules.standard.tower.tower_controller import TowerController
import time


@instance()
class TowerAttackController:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.event_service = registry.get_instance("event_service")
        self.playfield_controller = registry.get_instance("playfield_controller")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.public_channel_service = registry.get_instance("public_channel_service")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS tower_attacker (id INT PRIMARY KEY AUTO_INCREMENT, att_org_name VARCHAR(50) NOT NULL, att_faction VARCHAR(10) NOT NULL, "
                     "att_char_id INT, att_char_name VARCHAR(20) NOT NULL, att_level INT NOT NULL, att_ai_level INT NOT NULL, att_profession VARCHAR(15) NOT NULL, "
                     "x_coord INT NOT NULL, y_coord INT NOT NULL, is_victory SMALLINT NOT NULL, "
                     "tower_battle_id INT NOT NULL, created_at INT NOT NULL)")
        self.db.exec("CREATE TABLE IF NOT EXISTS tower_battle (id INT PRIMARY KEY AUTO_INCREMENT, playfield_id INT NOT NULL, site_number INT NOT NULL, "
                     "def_org_name VARCHAR(50) NOT NULL, def_faction VARCHAR(10) NOT NULL, is_finished INT NOT NULL, battle_type VARCHAR(20) NOT NULL, last_updated INT NOT NULL)")

        self.command_alias_service.add_alias("victory", "attacks")

    @command(command="attacks", params=[NamedParameters(["page"])], access_level="all",
             description="Show recent tower attacks and victories")
    def attacks_cmd(self, request, named_params):
        page = int(named_params.page or "1")

        page_size = 30
        offset = (page - 1) * page_size

        sql = """
            SELECT
                b.*,
                a.*,
                COALESCE(a.att_level, 0) AS att_level,
                COALESCE(a.att_ai_level, 0) AS att_ai_level,
                p.short_name,
                b.id AS battle_id
            FROM
                tower_battle b
                LEFT JOIN tower_attacker a ON
                    a.tower_battle_id = b.id
                LEFT JOIN playfields p ON
                    p.id = b.playfield_id
            ORDER BY
                b.last_updated DESC,
                a.created_at DESC
            LIMIT %d, %d
        """ % (offset, page_size)

        data = self.db.query(sql)
        t = int(time.time())

        blob = self.check_for_all_towers_channel()

        if page > 1:
            blob += "   " + self.text.make_chatcmd("<< Page %d" % (page - 1), self.get_chat_command(page - 1))
        if len(data) > 0:
            blob += "   Page " + str(page)
            blob += "   " + self.text.make_chatcmd("Page %d >>" % (page + 1), self.get_chat_command(page + 1))
            blob += "\n"

        current_battle_id = -1
        for row in data:
            if current_battle_id != row.battle_id:
                blob += "\n<pagebreak>"
                current_battle_id = row.battle_id
                blob += self.format_battle_info(row, t)
                blob += self.text.make_chatcmd("More Info", "/tell <myname> attacks battle %d" % row.battle_id) + "\n"
                blob += "<header2>Attackers:<end>\n"

            blob += "<tab>" + self.format_attacker(row) + "\n"

        return ChatBlob("Tower Attacks", blob)

    @command(command="attacks", params=[Const("battle"), Int("battle_id")], access_level="all",
             description="Show battle info for a specific battle")
    def attacks_battle_cmd(self, request, _, battle_id):
        battle = self.db.query_single("SELECT b.*, p.short_name FROM tower_battle b LEFT JOIN playfields p ON p.id = b.playfield_id WHERE b.id = ?", [battle_id])
        if not battle:
            return "Could not find battle with ID <highlight>%d<end>." % battle_id

        t = int(time.time())

        attackers = self.db.query("SELECT * FROM tower_attacker WHERE tower_battle_id = ? ORDER BY created_at DESC", [battle_id])

        first_activity = attackers[-1].created_at if len(attackers) > 0 else battle.last_updated

        blob = self.check_for_all_towers_channel()
        blob += self.format_battle_info(battle, t)
        blob += "Duration: <highlight>%s<end>\n\n" % self.util.time_to_readable(battle.last_updated - first_activity)
        blob += "<header2>Attackers:<end>\n"

        for row in attackers:
            blob += "<tab>" + self.format_attacker(row)
            blob += " " + self.format_timestamp(row.created_at, t)
            blob += "\n"

        return ChatBlob("Battle Info %d" % battle_id, blob)

    @event(event_type=TowerController.TOWER_ATTACK_EVENT, description="Record tower attacks", is_hidden=True)
    def tower_attack_event(self, event_type, event_data):
        t = int(time.time())
        site_number = self.find_closest_site_number(event_data.location.playfield.id, event_data.location.x_coord, event_data.location.y_coord)

        attacker = event_data.attacker or {}
        defender = event_data.defender

        battle = self.find_or_create_battle(event_data.location.playfield.id, site_number, defender.org_name, defender.faction, "attack", t)

        self.db.exec("INSERT INTO tower_attacker (att_org_name, att_faction, att_char_id, att_char_name, att_level, att_ai_level, att_profession, "
                     "x_coord, y_coord, is_victory, tower_battle_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     [attacker.get("org_name", ""), attacker.get("faction", ""), attacker.get("char_id", 0), attacker.get("name", ""), attacker.get("level", 0),
                      attacker.get("ai_level", 0), attacker.get("profession", ""), event_data.location.x_coord, event_data.location.y_coord, 0, battle.id, t])

    @event(event_type=TowerController.TOWER_VICTORY_EVENT, description="Record tower victories", is_hidden=True)
    def tower_victory_event(self, event_type, event_data):
        t = int(time.time())

        if event_data.type == "attack":
            row = self.get_last_attack(
                event_data.winner.faction, event_data.winner.org_name, event_data.loser.faction, event_data.loser.org_name,
                event_data.location.playfield.id, t)

            if not row:
                site_number = 0
                is_finished = 1
                self.db.exec("INSERT INTO tower_battle (playfield_id, site_number, def_org_name, def_faction, is_finished, battle_type, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             [event_data.location.playfield.id, site_number, event_data.loser.org_name, event_data.loser.faction, is_finished, event_data.type, t])
                battle_id = self.db.last_insert_id()

                attacker = event_data.winner or {}
                self.db.exec("INSERT INTO tower_attacker (att_org_name, att_faction, att_char_id, att_char_name, att_level, att_ai_level, att_profession, "
                             "x_coord, y_coord, is_victory, tower_battle_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             [attacker.get("org_name", ""), attacker.get("faction", ""), attacker.get("char_id", 0), attacker.get("name", ""), attacker.get("level", 0),
                              attacker.get("ai_level", 0), attacker.get("profession", ""), 0, 0, 0, battle_id, t])
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

    def format_attacker(self, row):
        if row.att_char_name:
            level = ("%d/<green>%d<end>" % (row.att_level, row.att_ai_level)) if row.att_ai_level > 0 else "%d" % row.att_level
            org = row.att_org_name + " " if row.att_org_name else ""
            victor = " - <notice>Winner!<end>" if row.is_victory else ""
            return "%s (%s %s) %s(%s)%s" % (row.att_char_name, level, row.att_profession, org, row.att_faction, victor)
        else:
            return "Unknown attacker"

    def find_closest_site_number(self, playfield_id, x_coord, y_coord):
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
                *
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
            return battle
        else:
            self.db.exec("INSERT INTO tower_battle (playfield_id, site_number, def_org_name, def_faction, is_finished, battle_type, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         [playfield_id, site_number, org_name, faction, is_finished, battle_type, t])
            return self.db.query_single("SELECT * FROM tower_battle WHERE id = ?", [self.db.last_insert_id()])

    def get_last_attack(self, att_faction, att_org_name, def_faction, def_org_name, playfield_id, t):
        last_updated = t - (8 * 3600)
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

    def format_battle_info(self, row, t):
        blob = ""
        defeated = " - <notice>Defeated!<end>" if row.is_finished else ""
        blob += "Site: <highlight>%s %s<end>\n" % (row.short_name, row.site_number or "?")
        blob += "Defender: <highlight>%s<end> (%s)%s\n" % (row.def_org_name, row.def_faction, defeated)
        blob += "Last Activity: %s\n" % self.format_timestamp(row.last_updated, t)
        return blob

    def format_timestamp(self, t, current_t):
        return "<highlight>%s<end> (%s ago)" % (self.util.format_datetime(t), self.util.time_to_readable(current_t - t))

    def get_chat_command(self, page):
        return "/tell <myname> attacks --page=%d" % page

    def check_for_all_towers_channel(self):
        if not self.public_channel_service.get_channel_name(TowerController.ALL_TOWERS_ID):
            return "Notice: The bot must belong to an org and be promoted to a rank that is high enough to have the All Towers channel (e.g., Squad Commander) in order for the <symbol>attacks command to work correctly.\n\n"
        else:
            return ""
