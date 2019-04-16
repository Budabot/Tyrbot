from core.command_param_types import Any
from core.command_request import CommandRequest
from core.db import DB
from core.decorators import instance, command


@instance()
class LogController:

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")

    @command(command="logon", params=[Any("logon_message")], access_level="member",
             description="Sets your own custom logon message")
    def set_logon(self, request: CommandRequest, logon_message):
        if self.db.query_single("SELECT logon FROM log_messages WHERE char_id=?;", [request.sender.char_id]):
            self.db.query_single("UPDATE log_messages SET logon=? WHERE char_id=?;",
                                 [logon_message, request.sender.char_id])
        else:
            self.db.query_single("INSERT INTO log_messages (char_id, logon) VALUES(?, ?);",
                                 [request.sender.char_id, logon_message])
        return "Your new logon message is: %s" % logon_message

    @command(command="logoff", params=[Any("logoff_message")], access_level="member",
             description="Sets your own custom logoff message")
    def set_logoff(self, request: CommandRequest, logoff_message):
        if self.db.query_single("SELECT logoff FROM log_messages WHERE char_id=?;", [request.sender.char_id]):
            self.db.query_single("UPDATE log_messages SET logoff=? WHERE char_id=?;",
                                 [logoff_message, request.sender.char_id])
        else:
            self.db.query_single("INSERT INTO log_messages (char_id, logoff) VALUES(?, ?);",
                                 [request.sender.char_id, logoff_message])
        return "Your new logoff message is: %s" % logoff_message

    def get_logon(self, char_id):
        row = self.db.query_single("SELECT * FROM log_messages WHERE char_id=?", [char_id])
        if row is not None:
            if row.logon:
                return "<grey>" + row.logon + "<end>"
        return ""

    def get_logoff(self, char_id):
        row = self.db.query_single("SELECT * FROM log_messages WHERE char_id=?", [char_id])
        if row is not None:
            if row.logoff:
                return "<grey>" + row.logoff + "<end>"
        return ""
