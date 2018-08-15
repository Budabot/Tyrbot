from core.chat_blob import ChatBlob
from core.command_param_types import Any
from core.decorators import instance, command, event
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
        self.event_service = registry.get_instance("event_service")
        self.playfield_controller = registry.get_instance("playfield_controller")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS tower_attack (id INT NOT NULL PRIMARY KEY AUTO_INCREMENT, created_at INT NOT NULL, att_org_name VARCHAR(50) NOT NULL, "
                     "att_faction VARCHAR(10) NOT NULL, att_char_id INT, att_name VARCHAR(20) NOT NULL, att_level INT NOT NULL, att_ai_level INT NOT NULL, att_profession VARCHAR(15) NOT NULL,"
                     "def_org_name VARCHAR(50) NOT NULL, def_faction VARCHAR(10) NOT NULL, playfield_id INT NOT NULL, site_number INT NOT NULL, "
                     "x_coord INT NOT NULL, y_coord INT NOT NULL)")

    @command(command="attacks", params=[], description="Show recent tower attacks", access_level="all")
    def attacks_cmd(self, request):
        pass

    @event(event_type=TowerController.TOWER_ATTACK_EVENT, description="Record tower attacks")
    def tower_attack_event(self, event_type, event_data):
        self.logger.info("tower attack: " + str(event_data))

        site_number = self.find_closest_site_number(event_data.location.playfield.id, event_data.location.x_coord, event_data.location.y_coord)

        attacker = event_data.attacker or {}
        defender = event_data.defender
        location = event_data.location

        self.db.exec("INSERT INTO tower_attack (att_org_name, att_faction, att_char_id, att_char_name, att_level, att_ai_level, att_profession, def_org_name, def_faction, "
                     "playfield_id, site_number, x_coord, y_coord, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     [attacker.get("org_name", ""), attacker.get("faction", ""), attacker.get("char_id", 0), attacker.get("name", ""), attacker.get("level", 0),
                      attacker.get("ai_level", 0), attacker.get("profession", ""), defender.org_name, defender.faction, location.playfield.id,
                      site_number, event_data.location.x_coord, event_data.location.y_coord, int(time.time())])

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

        row = self.db.query_single(sql, [playfield_id, x_coord, y_coord])
        if row:
            return row.site_number
        else:
            return 0
