import time

from core.chat_blob import ChatBlob
from core.command_param_types import Const, Options, Int
from core.decorators import instance, command, timerevent
from core.tyrbot import Tyrbot


@instance()
class AllianceAccessController:
    ALLIANCE_ACCESS_LEVEL = "alliance_member"

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.setting_service = registry.get_instance("setting_service")
        self.pork_service = registry.get_instance("pork_service")
        self.access_service = registry.get_instance("access_service")
        self.org_pork_service = registry.get_instance("org_pork_service")

    def pre_start(self):
        self.access_service.register_access_level(self.ALLIANCE_ACCESS_LEVEL, 85, self.alliance_member_access_level_handler)

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS alliance_org (org_id INT PRIMARY KEY, name VARCHAR(50) NOT NULL, faction VARCHAR(10) NOT NULL, "
                     "created_at INT NOT NULL, created_by INT NOT NULL)")

    @command(command="alliance", params=[], access_level="admin",
             description="Show the orgs in the alliance")
    def alliance_list_cmd(self, request):
        blob = ""
        data = self.db.query("SELECT org_id, name FROM alliance_org ORDER BY name ASC")
        for row in data:
            blob += f"<highlight>{row.name}</highlight> ({row.org_id})\n"

        return ChatBlob("Alliance Orgs (%d)" % len(data), blob)

    @command(command="alliance", params=[Const("add"), Int("org_id")], access_level="admin",
             description="Add an org to the alliance")
    def alliance_add_cmd(self, request, _, org_id):
        alliance_org = self.get_alliance_org(org_id)
        if alliance_org:
            return f"Org <highlight>{alliance_org.name}</highlight> ({org_id}) already belongs to the alliance."

        request.reply(f"Downloading org info for {org_id}...")
        org_info = self.org_pork_service.get_org_info(org_id)
        if not org_info:
            return f"Could not find org with id <highlight>{org_id}</highlight>."

        self.db.exec("INSERT INTO alliance_org (org_id, name, faction, created_at, created_by) VALUES (?, ?, ?, ?, ?)",
                     [org_id, org_info.org_info.name, org_info.org_info.faction, int(time.time()), request.sender.char_id])

        return f"Org <highlight>{org_info.org_info.name}</highlight> ({org_id}) has been added to the alliance successfully."

    @command(command="alliance", params=[Options(["rem", "remove"]), Int("org_id")], access_level="admin",
             description="Remove an org from, the alliance")
    def alliance_rem_cmd(self, request, _, org_id):
        alliance_org = self.get_alliance_org(org_id)
        if not alliance_org:
            return f"Org <highlight>{alliance_org.name}</highlight> ({org_id}) does not belong to the alliance."

        self.db.exec("DELETE FROM alliance_org WHERE org_id = ?", [org_id])

        return f"Org <highlight>{alliance_org.name}</highlight> ({org_id}) has been removed from the alliance successfully."

    @timerevent(budatime="24h", description="Download the org rosters for the alliance orgs", is_system=True)
    def download_alliance_org_rosters_event(self, event_type, event_data):
        data = self.db.query("SELECT org_id FROM alliance_org")
        for row in data:
            self.org_pork_service.get_org_info(row.org_id)

    def get_alliance_org(self, org_id):
        return self.db.query_single("SELECT name, org_id FROM alliance_org WHERE org_id = ?", [org_id])

    def alliance_member_access_level_handler(self, char_id):
        row = self.db.query_single("SELECT 1 FROM player p JOIN alliance_org a ON p.org_id = a.org_id WHERE p.char_id = ?", [char_id])
        return row is not None
