from core import db, command_request
from core.command_param_types import Any
from core.command_request import CommandRequest
from core.db import DB
from core.decorators import instance, command, event

@instance()
class LogController:

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db: DB = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.pork_service = registry.get_instance("pork_service")
        self.character_service = registry.get_instance("character_service")
        self.discord_controller = registry.get_instance("discord_controller")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.alts_service = registry.get_instance("alts_service")
        self.alts_controller = registry.get_instance("alts_controller")

    @command(command="logon", params=[Any("logon")], access_level="member",
             description="Sets your own custom logon message")
    def set_logon(self, request: CommandRequest, logon):
        if self.db.query_single("SELECT logon FROM logmessages WHERE char_id=?;", [request.sender.char_id]):
            self.db.query_single("UPDATE logmessages SET logon=? WHERE char_id=?;", [logon, request.sender.char_id])
        else:
            self.db.query_single("INSERT INTO logmessages (char_id, logon) VALUES(?, ?);",
                                 [request.sender.char_id], logon)
        return "Your new logon message is: %s" % logon

    @command(command="logoff", params=[Any("logoff")], access_level="member",
             description="Sets your own custom logoff message")
    def set_logoff(self, request: CommandRequest, logoff):
        if self.db.query_single("SELECT logoff FROM logmessages WHERE char_id=?;", [request.sender.char_id]):
            self.db.query_single("UPDATE logmessages SET logoff=? WHERE char_id=?;", [logoff, request.sender.char_id])
        else:
            self.db.query_single("INSERT INTO logmessages (char_id, logoff) VALUES(?, ?);",
                                 [request.sender.char_id], logoff)
        return "Your new logoff message is: %s" % logoff
