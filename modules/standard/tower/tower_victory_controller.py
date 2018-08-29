from core.chat_blob import ChatBlob
from core.decorators import instance, command, event
from core.logger import Logger
from modules.standard.tower.tower_controller import TowerController
import time


@instance()
class TowerVictoryController:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.event_service = registry.get_instance("event_service")
        self.playfield_controller = registry.get_instance("playfield_controller")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS tower_victory (id INT NOT NULL PRIMARY KEY AUTO_INCREMENT, win_org_name VARCHAR(50) NOT NULL, "
                     "win_faction VARCHAR(10) NOT NULL, lose_org_name VARCHAR(50) NOT NULL, lose_faction VARCHAR(10) NOT NULL, attack_id INT, "
                     "playfield_id INT NOT NULL, created_at INT NOT NULL)")

    @command(command="victory", params=[], description="Show recent tower victories", access_level="all")
    def victories_cmd(self, request):
        data = self.db.query("SELECT v.*, a.site_number, p.short_name FROM tower_victory v "
                             "LEFT JOIN tower_attack a ON v.attack_id = a.id "
                             "LEFT JOIN playfields p ON a.playfield_id = p.id "
                             "ORDER BY created_at DESC LIMIT 15")
        t = int(time.time())

        blob = ""
        for row in data:
            blob += "<pagebreak>"
            blob += "Time: <highlight>%s<end> (%s ago)\n" % (self.util.format_datetime(row.created_at), self.util.time_to_readable(t - row.created_at))
            blob += "Winner: <highlight>%s<end> (%s)\n" % (row.win_org_name, row.win_faction)
            blob += "Loser: <highlight>%s<end> (%s)\n" % (row.lose_org_name, row.lose_faction)
            blob += "Site: <highlight>%s %d<end>\n" % (row.short_name or "?", row.site_number or "?")
            blob += "\n"

        return ChatBlob("Tower Victories", blob)

    @event(event_type=TowerController.TOWER_VICTORY_EVENT, description="Record tower victories")
    def tower_victory_event(self, event_type, event_data):
        self.logger.info("tower victory: " + str(event_data))

        t = int(time.time())
        last_attack_t = t - (7 * 3600)

        if event_data.type == "attack":
            attack_id = self.get_last_attack_id(
                event_data.winner.faction, event_data.winner.org_name, event_data.loser.faction, event_data.loser.org_name,
                event_data.location.playfield.id, last_attack_t)
        elif event_data.type == "terminated":
            attack_id = 0
        else:
            raise Exception("Unknown victory event type: '%s'" % event_data.type)

        self.db.exec("INSERT INTO tower_victory (win_org_name, win_faction, lose_org_name, lose_faction, attack_id, playfield_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     [event_data.winner.org_name, event_data.winner.faction, event_data.loser.org_name, event_data.loser.faction,
                      attack_id, event_data.location.playfield.id, t])

    def get_last_attack_id(self, att_faction, att_org_name, def_faction, def_org_name, playfield_id, t):
        sql = """
            SELECT
                id
            FROM
                tower_attack
            WHERE
                att_faction = ?
                AND att_org_name = ?
                AND def_faction = ?
                AND def_org_name = ?
                AND playfield_id = ?
                AND created_at >= ?
            ORDER BY
                created_at DESC
            LIMIT 1"""

        row = self.db.query_single(sql, [att_faction, att_org_name, def_faction, def_org_name, playfield_id, t])
        if row:
            return row.id
        else:
            return 0
