from core.decorators import instance, event, timerevent
from core.logger import Logger


@instance()
class OrgController:
    ORG_BUDDY_TYPE = "org"

    MODE_AUTO = "auto"
    MODE_IGNORE = "ignore"
    MODE_MANUAL = "manual"

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.buddy_manager = registry.get_instance("buddy_manager")
        self.public_channel_manager = registry.get_instance("public_channel_manager")
        self.access_manager = registry.get_instance("access_manager")
        self.org_pork_manager = registry.get_instance("org_pork_manager")

    def pre_start(self):
        self.access_manager.register_access_level("org", 60, self.check_org_member)

    @event(event_type="connect", description="Add members as buddies of the bot on startup")
    def handle_connect_event(self, event_type, event_data):
        for row in self.get_all_org_members():
            self.buddy_manager.add_buddy(row.char_id, self.ORG_BUDDY_TYPE)

    @timerevent(budatime="24h", description="Download the org roster")
    def handle_connect_event(self, event_type, event_data):
        org_id = self.public_channel_manager.get_org_id()
        if org_id:
            db_members = {}
            for row in self.get_all_org_members():
                db_members[row.char_id] = row.mode

            self.logger.info("Updating org roster for org_id %d" % org_id)
            org_info = self.org_pork_manager.get_org_info(org_id)
            if org_info:
                for roster_member in org_info["org_members"]:
                    char_id = roster_member["char_id"]
                    db_member = db_members.get(char_id, None)

                    if not db_member:
                        self.add_org_member(char_id, self.MODE_AUTO)
                    elif db_member == self.MODE_AUTO:
                        # do nothing
                        del db_members[char_id]
                    elif db_member == self.MODE_MANUAL:
                        self.update_org_member(char_id, self.MODE_AUTO)
                        del db_members[char_id]
                    elif db_member == self.MODE_IGNORE:
                        # do nothing
                        del db_members[char_id]

                for char_id, mode in db_members.items():
                    if mode == self.MODE_AUTO:
                        self.remove_org_member(char_id)
                    elif mode == self.MODE_IGNORE:
                        self.remove_org_member(char_id)
                    elif mode == self.MODE_MANUAL:
                        # do nothing
                        pass

    def get_org_member(self, char_id):
        return self.db.query_single("SELECT char_id FROM org_member WHERE char_id = ?", [char_id])

    def get_all_org_members(self):
        return self.db.query("SELECT char_id, mode FROM org_member")

    def add_org_member(self, char_id, mode):
        return self.db.exec("INSERT INTO org_member (char_id, mode) VALUES (?, ?)", [char_id, mode])

    def remove_org_member(self, char_id):
        return self.db.exec("DELETE FROM org_member WHERE char_id = ?", [char_id])

    def update_org_member(self, char_id, mode):
        return self.db.exec("UPDATE org_member SET mode = ? WHERE char_id = ?", [mode, char_id])

    def check_org_member(self, char_id):
        return self.get_org_member(char_id) is not None
