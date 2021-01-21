from core.chat_blob import ChatBlob
from core.command_param_types import Character
from core.decorators import instance, command
from core.logger import Logger


@instance()
class LastSeenController:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.character_service = registry.get_instance("character_service")
        self.public_channel_service = registry.get_instance("public_channel_service")

    @command(command="lastseen", params=[Character("character")], access_level="admin",
             description="Show the last time an org member was online (on any alt)")
    def lastseen_cmd(self, request, char):
        if not self.public_channel_service.get_org_id:
            return "Error! Bot must be in an org in order to use this command."

        sql = """
            SELECT
                p.*,
                o.last_seen
            FROM
                player p
                LEFT JOIN alts a ON p.char_id = a.char_id
                JOIN org_member o ON p.char_id = o.char_id
            WHERE
                o.last_seen != 0 AND (
                    p.char_id = ?
                    OR a.group_id = (SELECT group_id FROM alts WHERE char_id = ?)
                )
            ORDER BY
                o.last_seen DESC,
                p.name ASC,
                p.level DESC
        """

        data = self.db.query(sql, [char.char_id, char.char_id])
        blob = ""
        if len(data) == 0:
            blob += "Note: <highlight>%s</highlight> must be in the same organization as the bot in order to track <highlight>lastseen</highlight> data." % char.name

        for row in data:
            blob += "<highlight>%s</highlight> last seen at %s\n" % (row.name, self.util.format_datetime(row.last_seen))

        return ChatBlob("Last Seen for %s (%d)" % (char.name, len(data)), blob)
