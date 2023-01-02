import time

from core.command_param_types import Any, Const
from core.command_request import CommandRequest
from core.db import DB
from core.decorators import instance, command


@instance()
class LogController:

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.util = registry.get_instance("util")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS log_messages (char_id INT NOT NULL PRIMARY KEY, logon TEXT, logon_set_dt INT NOT NULL, logoff TEXT, logoff_set_dt INT NOT NULL)")

    @command(command="logon", params=[], access_level="member", description="Check your current logon message")
    def check_current_logon(self, request):
        current_logon = self.get_log_message(request.sender.char_id, "logon", show_time_set=True)
        if current_logon:
            return "%s's logon message is: %s" % (request.sender.name, current_logon)
        else:
            return "Your logon message has not been set."

    @command(command="logon", params=[Const("clear")], access_level="member", description="Clear your logon message")
    def clear_logon(self, request, params):
        if self.db.query_single("SELECT logon FROM log_messages WHERE char_id = ?", [request.sender.char_id]):
            self.db.exec("UPDATE log_messages SET logon = NULL, logon_set_dt = ? WHERE char_id = ?", [int(time.time()), request.sender.char_id])
        return "Your logon message has been cleared."

    @command(command="logon", params=[Any("logon_message")], access_level="member", description="Set your logon message")
    def set_logon(self, request: CommandRequest, logon_message):
        if self.db.query_single("SELECT logon FROM log_messages WHERE char_id = ?", [request.sender.char_id]):
            self.db.exec("UPDATE log_messages SET logon = ?, logon_set_dt = ? WHERE char_id = ?", [logon_message, int(time.time()), request.sender.char_id])
        else:
            self.db.exec("INSERT INTO log_messages (char_id, logon) VALUES(?, ?)", [request.sender.char_id, logon_message])
        return "Your new logon message is: %s" % logon_message

    @command(command="logoff", params=[], access_level="member", description="Check your current logoff message")
    def check_current_logoff(self, request):
        current_logoff = self.get_log_message(request.sender.char_id, "logoff", show_time_set=True)
        if current_logoff:
            return "%s's logoff message is: %s" % (request.sender.name, current_logoff)
        else:
            return "Your logoff message has not been set."

    @command(command="logoff", params=[Const("clear")], access_level="member", description="Clear your logoff message")
    def clear_logoff(self, request, params):
        if self.db.query_single("SELECT logoff FROM log_messages WHERE char_id = ?", [request.sender.char_id]):
            self.db.exec("UPDATE log_messages SET logoff = NULL, logoff_set_dt = ? WHERE char_id = ?", [int(time.time()), request.sender.char_id])
        return "Your logoff message has been cleared."

    @command(command="logoff", params=[Any("logoff_message")], access_level="member", description="Set your logoff message")
    def set_logoff(self, request: CommandRequest, logoff_message):
        if self.db.query_single("SELECT logoff FROM log_messages WHERE char_id = ?", [request.sender.char_id]):
            self.db.exec("UPDATE log_messages SET logoff = ?, logoff_set_dt = ? WHERE char_id = ?", [logoff_message, int(time.time()), request.sender.char_id])
        else:
            self.db.exec("INSERT INTO log_messages (char_id, logoff) VALUES(?, ?)", [request.sender.char_id, logoff_message])
        return "Your new logoff message is: %s" % logoff_message

    def get_log_message(self, char_id, log_message_type, show_time_set=False):
        row = self.db.query_single("SELECT * FROM log_messages WHERE char_id = ?", [char_id])
        if row and row[log_message_type]:
            msg = "<grey>%s</grey>" % row[log_message_type]
            if show_time_set and row[log_message_type + "_set_dt"] > 0:
                msg += " [%s ago]" % self.util.time_to_readable(int(time.time()) - row[log_message_type + "_set_dt"])
        else:
            msg = ""

        return msg

    def get_logon(self, char_id):
        return self.get_log_message(char_id, "logon")

    def get_logoff(self, char_id):
        return self.get_log_message(char_id, "logoff")
