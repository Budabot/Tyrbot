import requests
import time

from core.command_param_types import Options, Any, Int
from core.decorators import instance, event, command
from core.logger import Logger
from modules.core.org_members.org_member_controller import OrgMemberController
from core.setting_types import BooleanSettingType
from modules.standard.helpbot.playfield_controller import PlayfieldController
from modules.standard.tower.tower_messages_controller import TowerMessagesController


@instance()
class TowerScoutController:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.setting_service = registry.get_instance("setting_service")
        self.playfield_controller: PlayfieldController = registry.get_instance("playfield_controller")
        self.highway_websocket_controller = registry.get_instance("highway_websocket_controller")

    def start(self):
        self.db.load_sql_file(self.module_dir + "/" + "scout_info.sql")

        self.setting_service.register(self.module_name, "auto_scout_enable", True, BooleanSettingType(), "Enable Auto Scout")
        self.setting_service.register_change_listener("auto_scout_enable", self.auto_scout_update)

        self.auto_scout_update("auto_scout_enable", None, self.setting_service.get("auto_scout_enable").get_value())

    @command(command="scout", params=[Options(["rem", "remove"]), Any("playfield"), Int("site_number")], access_level=OrgMemberController.ORG_ACCESS_LEVEL,
             description="Removing scouting information for a tower site")
    def scout_remove_cmd(self, request, _, playfield_name, site_number):
        playfield = self.playfield_controller.get_playfield_by_name_or_id(playfield_name)
        if not playfield:
            return f"Could not find playfield <highlight>{playfield_name}</highlight>."

        num_rows = self.db.exec("DELETE FROM scout_info WHERE playfield_id = ? AND site_number = ?",
                                [playfield.id, site_number])

        if num_rows == 0:
            return f"No scouting information exists for <highlight>{playfield.long_name} {site_number}</highlight>."
        else:
            return f"Scouting information for <highlight>{playfield.long_name} {site_number}</highlight> removed successfully."

    @event(event_type=TowerMessagesController.TOWER_VICTORY_EVENT, description="Remove scout info for tower sites that are destroyed", is_system=True)
    def tower_scout_info_cleanup_event(self, event_type, event_data):
        if event_data.location.site_number:
            self.db.exec("DELETE FROM scout_info WHERE playfield_id = ? AND site_number = ?",
                         [event_data.location.playfield.id, event_data.location.site_number])
        else:
            self.db.exec("DELETE FROM scout_info WHERE playfield_id = ? AND faction = ? AND org_name = ?",
                         [event_data.location.playfield.id, event_data.loser.faction, event_data.loser.org_name])

    @event(event_type=TowerMessagesController.TOWER_VICTORY_EVENT, description="Update penalty time on tower victory", is_system=True)
    def tower_victory_update_penalty_event(self, event_type, event_data):
        self.update_penalty_time(event_data.timestamp, event_data.winner.org_name, event_data.winner.faction)

    @event(event_type=TowerMessagesController.TOWER_ATTACK_EVENT, description="Update penalty time on tower attack", is_system=True)
    def tower_attack_update_penalty_event(self, event_type, event_data):
        self.update_penalty_time(event_data.timestamp, event_data.attacker.org_name, event_data.attacker.faction)

    def update_penalty_time(self, t, org_name, faction):
        if not org_name or not faction:
            return

        data = self.db.query("SELECT playfield_id, site_number, org_name, faction, penalty_duration, penalty_until, created_at "
                             "FROM scout_info "
                             "WHERE org_name LIKE ? AND faction LIKE ? AND created_at <= ?", [org_name, faction, t])

        for row in data:
            penalty_duration = ((row.created_at - t) % 3600) + 3600
            penalty_until = t + penalty_duration

            if row.penalty_until < penalty_until:
                self.db.exec("UPDATE scout_info SET penalty_duration = ?, penalty_until = ? "
                             "WHERE playfield_id = ? AND site_number = ?", [penalty_duration, penalty_until, row.playfield_id, row.site_number])

    def handle_websocket_message(self, obj):
        def extract_and_update(t, site):
            self.update_scout_info(t, site["playfield_id"], site["site_id"], site.get("org_id"), site.get("org_name"), site.get("org_faction") or "Unknown",
                site.get("ql"), site.get("plant_time"), (site.get("ct_pos") or {}).get("x"), (site.get("ct_pos") or {}).get("y"), site.get("num_conductors"), site.get("num_turrets"))
    
        if obj.type == "room-info":
            headers = {"User-Agent": f"Tyrbot {self.bot.version}"}
            r = requests.get("https://towers.aobots.org/api/sites", headers=headers, timeout=5)
            result = r.json()

            t = int(time.time())
            for site in result:
                extract_and_update(t, site)

            data = self.db.query("SELECT org_name, faction, count(1), max(created_at) FROM scout_info WHERE created_at > ? GROUP BY org_name, faction", [t - 7200])
            for row in data:
                self.update_penalty_time(t, row.org_name, row.faction)
        elif obj.type == "message":
            if obj.body.get("type") == "update_site":  # {'attacker': {'ai_level': 3, 'breed': None, 'character_id': 1866227579, 'faction': 'Neutral', 'gender': None, 'level': 27, 'name': 'Eggbeatr', 'org': {'faction': 'Neutral', 'id': 1986585, 'name': 'Normal Pvp'}, 'org_rank': 'Executive', 'profession': 'Enforcer'}, 'defender': {'faction': 'Clan', 'id': None, 'name': 'Fairy Tail'}, 'location': {'x': 1680, 'y': 2695}, 'penalizing_ended': None, 'playfield_id': 790, 'ql': 30, 'site_id': 3, 'timestamp': 1749668777, 'type': 'tower_attack'}
                site = obj.body
                t = int(time.time())
                extract_and_update(t, site)
            elif obj.body.get("type") == "tower_attack":  # {'center': {'x': 1700, 'y': 2780}, 'ct_pos': {'x': 1680, 'y': 2695}, 'enabled': True, 'gas': 25, 'max_ql': 30, 'min_ql': 15, 'name': 'Hound Land', 'num_conductors': 1, 'num_turrets': 2, 'org_faction': 'Clan', 'org_id': 6699, 'org_name': 'Fairy Tail', 'plant_time': 1712918999, 'playfield_id': 790, 'ql': 30, 'site_id': 3, 'timing': 'StaticEurope', 'type': 'update_site'}
                pass
            elif obj.body.get("type") == "tower_outcome":  # {'attacking_faction': 'Neutral', 'attacking_org': 'Normal Pvp', 'losing_faction': 'Omni', 'losing_org': 'Valhall Guardians', 'playfield_id': 791, 'site_id': 5, 'timestamp': 1749668427, 'type': 'tower_outcome'}
                pass
            elif obj.body.get("type") == "update_gas":
                pass
        
    def update_scout_info(self, t, playfield_id, site_number, org_id, org_name, faction, ql, plant_time, x_coord, y_coord, num_conductors, num_turrets):
        self.db.exec("DELETE FROM scout_info WHERE playfield_id = ? AND site_number = ?", [playfield_id, site_number])

        if org_id and x_coord and y_coord:
            tower_site_info = self.get_tower_site_info(playfield_id, site_number)
            close_time = plant_time % 86400
            if tower_site_info.close_time:
                close_time = tower_site_info.close_time + (close_time % 3600)

            self.db.exec("INSERT INTO scout_info (playfield_id, site_number, ql, x_coord, y_coord, org_name, org_id, faction, close_time, "
                        "num_conductors, num_turrets, penalty_duration, penalty_until, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?)",
                        [playfield_id, site_number, ql, x_coord, y_coord, org_name, org_id, faction, close_time, num_conductors, num_turrets, plant_time, t])

    def get_tower_site_info(self, playfield_id, site_number):
        return self.db.query_single("SELECT playfield_id, site_number, min_ql, max_ql, x_coord, y_coord, close_time, site_name "
                                    "FROM tower_site "
                                    "WHERE playfield_id = ? AND site_number = ?",
                                    [playfield_id, site_number])

    def auto_scout_update(self, setting_name, old_value, new_value):
        if old_value:
            self.highway_websocket_controller.unregister_room_callback("tower_events", self.handle_websocket_message)
        if new_value:
            self.highway_websocket_controller.register_room_callback("tower_events", self.handle_websocket_message)
