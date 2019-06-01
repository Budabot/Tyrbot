import time

from core.chat_blob import ChatBlob
from core.decorators import instance, command, event
from core.logger import Logger
from core.public_channel_service import PublicChannelService


@instance()
class OrgActivityController:
    LEFT_ORG = [508, 45978487]
    KICKED_FROM_ORG = [508, 37093479]
    INVITED_TO_ORG = [508, 173558247]
    KICKED_INACTIVE_FROM_ORG = [508, 20908201]
    KICKED_ALIGNMENT_CHANGED = [501, 181448347]

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.character_service = registry.get_instance("character_service")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS org_activity (id INT PRIMARY KEY AUTO_INCREMENT, actor_char_id INT NOT NULL, actee_char_id INT NOT NULL, "
                     "action VARCHAR(20) NOT NULL, created_at INT NOT NULL)")

        self.command_alias_service.add_alias("orghistory", "orgactivity")

    @command(command="orgactivity", params=[], access_level="org_member",
             description="Show org member activity")
    def orgactivity_cmd(self, request):
        sql = """
            SELECT
                p1.name AS actor,
                p2.name AS actee, o.action,
                o.created_at
            FROM
                org_activity o
                LEFT JOIN player p1 ON o.actor_char_id = p1.char_id
                LEFT JOIN player p2 ON o.actee_char_id = p2.char_id
            ORDER BY
                o.created_at DESC
            LIMIT 40
        """
        data = self.db.query(sql)
        blob = ""
        for row in data:
            blob += self.format_org_action(row) + "\n"

        return ChatBlob("Org Activity", blob)

    @event(PublicChannelService.ORG_MSG_EVENT, "Record org member activity", is_hidden=True)
    def org_msg_event(self, event_type, event_data):
        ext_msg = event_data.extended_message
        if [ext_msg.category_id, ext_msg.instance_id] == self.LEFT_ORG:
            self.save_activity(ext_msg.params[0], ext_msg.params[0], "left")
        elif [ext_msg.category_id, ext_msg.instance_id] == self.KICKED_FROM_ORG:
            self.save_activity(ext_msg.params[0], ext_msg.params[1], "kicked")
        elif [ext_msg.category_id, ext_msg.instance_id] == self.INVITED_TO_ORG:
            self.save_activity(ext_msg.params[0], ext_msg.params[1], "invited")
        elif [ext_msg.category_id, ext_msg.instance_id] == self.KICKED_INACTIVE_FROM_ORG:
            self.save_activity(ext_msg.params[0], ext_msg.params[1], "removed")

    def save_activity(self, actor, actee, action):
        actor_id = self.character_service.resolve_char_to_id(actor)
        actee_id = self.character_service.resolve_char_to_id(actee) if actee else 0

        if not actor_id:
            self.logger.error("Could not get char_id for actor '%s'" % actor)

        if not actee_id:
            self.logger.error("Could not get char_id for actee '%s'" % actee)

        t = int(time.time())
        self.db.exec("INSERT INTO org_activity (actor_char_id, actee_char_id, action, created_at) VALUES (?, ?, ?, ?)", [actor_id, actee_id, action, t])

    def format_org_action(self, row):
        if row.action == "left":
            return "<highlight>%s<end> %s. %s" % (row.actor, row.action, self.util.format_datetime(row.created_at))
        else:
            return "<highlight>%s<end> %s <highlight>%s<end>. %s" % (row.actor, row.action, row.actee, self.util.format_datetime(row.created_at))
