from core.command_param_types import Options, Any, Int
from core.decorators import instance, event, command
from core.logger import Logger
from modules.core.org_members.org_member_controller import OrgMemberController

from modules.standard.helpbot.playfield_controller import PlayfieldController
from modules.standard.tower.tower_messages_controller import TowerMessagesController


@instance()
class TowerScoutController:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.pork_service = registry.get_instance("pork_service")
        self.playfield_controller: PlayfieldController = registry.get_instance("playfield_controller")

    def start(self):
        self.db.load_sql_file(self.module_dir + "/" + "scout_info.sql")

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

    @event(event_type=TowerMessagesController.TOWER_VICTORY_EVENT, description="Remove scout info for tower sites that are destroyed", is_system=True, is_enabled=False)
    def tower_scout_info_cleanup_event(self, event_type, event_data):
        if event_data.location.site_number:
            self.db.exec("DELETE FROM scout_info WHERE playfield_id = ? AND site_number = ?",
                         [event_data.location.playfield.id, event_data.location.site_number])
        else:
            self.db.exec("DELETE FROM scout_info WHERE playfield_id = ? AND faction = ? AND org_name = ?",
                         [event_data.location.playfield.id, event_data.loser.faction, event_data.loser.org_name])

    @event(event_type=TowerMessagesController.TOWER_VICTORY_EVENT, description="Update penalty time on tower victory", is_system=True, is_enabled=False)
    def tower_victory_update_penalty_event(self, event_type, event_data):
        self.update_penalty_time(event_data.battle_id, event_data.winner.org_name, event_data.winner.faction)

    @event(event_type=TowerMessagesController.TOWER_ATTACK_EVENT, description="Update penalty time on tower attack", is_system=True, is_enabled=False)
    def tower_attack_update_penalty_event(self, event_type, event_data):
        self.update_penalty_time(event_data.timestamp, event_data.attacker.org_name, event_data.attacker.faction)

    def update_penalty_time(self, t, org_name, faction):
        if not org_name or not faction:
            return

        data = self.db.query("SELECT playfield_id, site_number, org_name, faction, penalty_duration, penalty_until, created_at "
                             "FROM scout_info "
                             "WHERE org_name = ? AND faction = ? AND created_at <= ?", [org_name, faction, t])
        for row in data:
            penalty_duration = ((row.created_at - t) % 3600) + 3600
            penalty_until = t + penalty_duration

            if row.penalty_until < penalty_until:
                self.db.exec("UPDATE scout_info SET penalty_duration = ?, penalty_until = ? "
                             "WHERE playfield_id = ? AND site_number = ?", [penalty_duration, penalty_until, row.playfield_id, row.site_number])
