from core.buddy_service import BuddyService
from core.decorators import instance, event, timerevent
from core.logger import Logger


@instance()
class OrgMemberController:
    ORG_BUDDY_TYPE = "org_member"
    ORG_ACCESS_LEVEL = "org_member"

    MODE_AUTO = "auto"
    MODE_IGNORE = "ignore"
    MODE_MANUAL = "manual"

    ORG_MEMBER_LOGON_EVENT = "org_member_logon"
    ORG_MEMBER_LOGOFF_EVENT = "org_member_logoff"

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.buddy_service = registry.get_instance("buddy_service")
        self.public_channel_service = registry.get_instance("public_channel_service")
        self.access_service = registry.get_instance("access_service")
        self.org_pork_service = registry.get_instance("org_pork_service")
        self.event_service = registry.get_instance("event_service")

    def pre_start(self):
        self.event_service.register_event_type(self.ORG_MEMBER_LOGON_EVENT)
        self.event_service.register_event_type(self.ORG_MEMBER_LOGOFF_EVENT)
        self.access_service.register_access_level(self.ORG_ACCESS_LEVEL, 60, self.check_org_member)

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS org_member (char_id INT NOT NULL PRIMARY KEY, mode VARCHAR(7) NOT NULL)")

    @event(event_type="connect", description="Add members as buddies of the bot on startup")
    def handle_connect_event(self, event_type, event_data):
        for row in self.get_all_org_members():
            self.buddy_service.add_buddy(row.char_id, self.ORG_BUDDY_TYPE)

    @event(event_type=BuddyService.BUDDY_LOGON_EVENT, description="Check if buddy is an org member")
    def handle_buddy_logon_event(self, event_type, event_data):
        if self.get_org_member(event_data.char_id):
            self.event_service.fire_event(self.ORG_MEMBER_LOGON_EVENT, event_data)

    @event(event_type=BuddyService.BUDDY_LOGOFF_EVENT, description="Check if buddy is an org member")
    def handle_buddy_logoff_event(self, event_type, event_data):
        if self.get_org_member(event_data.char_id):
            self.event_service.fire_event(self.ORG_MEMBER_LOGOFF_EVENT, event_data)

    @timerevent(budatime="24h", description="Download the org_members roster")
    def download_org_roster_event(self, event_type, event_data):
        org_id = self.public_channel_service.get_org_id()
        if org_id:
            db_members = {}
            for row in self.get_all_org_members():
                db_members[row.char_id] = row.mode

            self.logger.info("Updating org_members roster for org_id %d" % org_id)
            org_info = self.org_pork_service.get_org_info(org_id)
            if org_info:
                for char_id, roster_member in org_info.org_members.items():
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
