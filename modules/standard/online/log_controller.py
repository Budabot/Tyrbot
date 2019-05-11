from core.command_param_types import Any, Const
from core.command_request import CommandRequest
from core.db import DB
from core.decorators import instance, command


@instance()
class LogController:

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")

    @command(command="logon", params=[], access_level="member", description="Check your current logon message")
    def check_current_logon(self, request):
        current_logon = self.get_logon(request.sender.char_id)
        if current_logon:
            return "%s's logon message is: %s" % (request.sender.name, current_logon)
        else:
            return "Your logon message has not been set."

    @command(command="logon", params=[Const("clear")], access_level="member", description="Clear your logon message")
    def clear_logon(self, request, params):
        if self.db.query_single("SELECT logon FROM log_messages WHERE char_id=?;", [request.sender.char_id]):
            self.db.exec("UPDATE log_messages SET logon=NULL WHERE char_id=?;",
                                 [request.sender.char_id])
        return "Your logon message has been cleared."

    @command(command="logon", params=[Any("logon_message")], access_level="member", description="Set your logon message")
    def set_logon(self, request: CommandRequest, logon_message):
        if self.db.query_single("SELECT logon FROM log_messages WHERE char_id=?;", [request.sender.char_id]):
            self.db.exec("UPDATE log_messages SET logon=? WHERE char_id=?;",
                                 [logon_message, request.sender.char_id])
        else:
            self.db.exec("INSERT INTO log_messages (char_id, logon) VALUES(?, ?);",
                                 [request.sender.char_id, logon_message])
        return "Your new logon message is: %s" % logon_message

    @command(command="logoff", params=[], access_level="member", description="Check your current logoff message")
    def check_current_logoff(self, request):
        current_logoff = self.get_logoff(request.sender.char_id)
        if current_logoff:
            return "%s's logoff message is: %s" % (request.sender.name, current_logoff)
        else:
            return "Your logoff message has not been set."

    @command(command="logoff", params=[Const("clear")], access_level="member", description="Clear your logoff message")
    def clear_logoff(self, request, params):
        if self.db.query_single("SELECT logoff FROM log_messages WHERE char_id=?;", [request.sender.char_id]):
            self.db.exec("UPDATE log_messages SET logoff=NULL WHERE char_id=?;",
                                 [request.sender.char_id])
        return "Your logoff message has been cleared."

    @command(command="logoff", params=[Any("logoff_message")], access_level="member", description="Set your logoff message")
    def set_logoff(self, request: CommandRequest, logoff_message):
        if self.db.query_single("SELECT logoff FROM log_messages WHERE char_id=?;", [request.sender.char_id]):
            self.db.exec("UPDATE log_messages SET logoff=? WHERE char_id=?;",
                                 [logoff_message, request.sender.char_id])
        else:
            self.db.exec("INSERT INTO log_messages (char_id, logoff) VALUES(?, ?);",
                                 [request.sender.char_id, logoff_message])
        return "Your new logoff message is: %s" % logoff_message

    def get_logon(self, char_id):
        row = self.db.query_single("SELECT * FROM log_messages WHERE char_id=?", [char_id])
        if row and row.logon:
            return "<grey>" + row.logon + "<end>"
        return ""

    def get_logoff(self, char_id):
        row = self.db.query_single("SELECT * FROM log_messages WHERE char_id=?", [char_id])
        if row and row.logoff:
            return "<grey>" + row.logoff + "<end>"
        return ""
