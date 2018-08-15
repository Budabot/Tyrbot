from core.tyrbot import Tyrbot
from core.db import DB
from core.decorators import command, instance, setting
from core.chat_blob import ChatBlob
from core.command_param_types import Options, Any, Int, Const
from core.lookup.character_service import CharacterService
from core.setting_types import NumberSettingType
from core.setting_service import SettingService
from core.text import Text
from core.alts.alts_service import AltsService
from core.util import Util
from core.access_service import AccessService
import time


@instance()
class PointsController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.access_service: AccessService = registry.get_instance("access_service")
        self.util: Util = registry.get_instance("util")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.alts_service: AltsService = registry.get_instance("alts_service")

    @setting(name="initial_points_value", value="0", description="How many points new accounts start with")
    def initial_points_value(self):
        return NumberSettingType()

    @command(command="bank", params=[Const("create"), Any("char")],
             description="Create a new account for given character name", access_level="admin")
    def bank_create_cmd(self, request, _, char: str):
        char = char.capitalize()
        char_id = self.character_service.resolve_char_to_id(char)
        alts_info = self.alts_service.get_alts(char_id)

        for alt in alts_info:
            sql = "SELECT char_id, disabled FROM points WHERE char_id = ? LIMIT 1"
            count = self.db.query_single(sql, [alt.char_id])

            if count:
                was_disabled = False

                if count.disabled == 1:
                    if self.db.exec("UPDATE points SET disabled = 0 WHERE char_id = ?", [alt.char_id]):
                        was_disabled = True

                if alt.char_id == char_id:
                    if was_disabled:
                        if self.add_log_entry(alt.char_id, request.sender.char_id,
                                              "Account was re-enabled by %s" % self.character_service.resolve_char_to_name(
                                                  request.sender.char_id)):
                            return "%s's account has been re-enabled." % char
                        else:
                            return "%s has an account, but failed to re-enable it." % char
                    else:
                        return "%s already has an account." % char
                else:
                    if was_disabled:
                        if self.add_log_entry(alt.char_id, request.sender.char_id,
                                              "Account was re-enabled by %s" % self.character_service.resolve_char_to_name(
                                                      request.sender.char_id)):
                            return "%s's (%s) account has been re-enabled." % (
                                char, self.character_service.resolve_char_to_name(alt.char_id))
                        else:
                            return "%s (%s) has an account, but failed to re-enable it." % (
                                char, self.character_service.resolve_char_to_name(alt.char_id))
                    else:
                        return "%s (%s) already has an account." % (
                            char, self.character_service.resolve_char_to_name(alt.char_id))

        main_info = alts_info.pop(0)
        changed_to_main = main_info.char_id == char_id

        initial_points = self.setting_service.get("initial_points_value").get_value()

        sql = "INSERT INTO points (char_id, points, created) VALUES (?,?,?)"
        if self.db.exec(sql, [main_info.char_id, initial_points, int(time.time())]) < 1:
            return "Failed to create an account for %s." % char

        if not self.add_log_entry(main_info.char_id, request.sender.char_id,
                                  "Account opened by %s" % request.sender.name):
            sql = "DELETE FROM points WHERE char_id = ?"
            self.db.exec(sql, [main_info.char_id])
            return "Failed to create an account for %s." % char

        name_reference = "%s (%s)" % (
            char, self.character_service.resolve_char_to_name(main_info.char_id)) if changed_to_main else char
        return "%s has had a new account opened." % name_reference

    @command(command="bank", params=[Const("close"), Any("char")],
             description="Close the account for given character name", access_level="admin")
    def close_account_cmd(self, request, _, char: str):
        char = char.capitalize()
        char_id = self.character_service.resolve_char_to_id(char)
        main_id = self.alts_service.get_main(char_id)

        sql = "UPDATE points SET disabled = 1 WHERE char_id = ?"
        if self.db.exec(sql, [main_id.char_id]) > 0:
            reason = "Account was closed by %s" % self.character_service.resolve_char_to_name(request.sender.char_id)
            if self.add_log_entry(main_id.char_id, request.sender.char_id, reason):
                name_reference = "%s (%s)" % (char, self.character_service.resolve_char_to_name(
                    main_id.char_id)) if main_id.char_id != char_id else char
                return "%s has had their account disabled. Logs have been preserved." % name_reference

        return "%s does not have an open account." % char

    @command(command="bank", params=[Options(["give", "take"]), Int("amount"), Any("char"), Any("reason")],
             description="Give or take points from character account", access_level="admin")
    def bank_give_take_cmd(self, request, action: str, amount: int, char: str, reason: str):
        char = char.capitalize()
        char_id = self.character_service.resolve_char_to_id(char)
        main_id = self.alts_service.get_main(char_id)

        sql = "SELECT * FROM points WHERE char_id = ?"
        points = self.db.query_single(sql, [main_id.char_id])

        if points:
            if points.disabled == 1:
                return "%s's account is disabled, altering the account is not possible." % char

            if points.points == 0 and action == "take":
                return "%s has 0 points - can't have less than 0 points." % char

            if amount > points.points and action == "take":
                amount = points.points

            new_points = amount if action == "give" else 0 - amount

            if not self.alter_points(points.points, main_id.char_id, new_points, request.sender.char_id, reason):
                return "Failed to alter %s's account." % char

            action = "taken from" if action == "take" else "added to"
            return "%s has had %d points %s their account." % (char, amount, action)

        return "%s does not have an account." % char

    @command(command="account", params=[Any("char", is_optional=True)], description="Look up account",
             access_level="all")
    def account_cmd(self, request, char: str):
        if char:
            char = char.capitalize()
            char_id = self.character_service.resolve_char_to_id(char)

            if not self.access_service.check_access(request.sender.char_id, "admin"):
                return "Only admins can see accounts of others."
        else:
            char_id = request.sender.char_id
            char = request.sender.name

        main_id = self.alts_service.get_main(char_id)

        blob = ""

        points_log = self.db.query("SELECT * FROM points_log WHERE char_id = ? ORDER BY time DESC LIMIT 50", [main_id.char_id])
        points = self.db.query_single("SELECT points, disabled FROM points WHERE char_id = ?", [main_id.char_id])

        main_name = self.character_service.resolve_char_to_name(main_id.char_id)
        alts_link = self.text.make_chatcmd("Alts", "/tell <myname> alts %s" % main_name)
        blob += "Holder of account: %s [%s]\n" % (main_name, alts_link)
        blob += "Points: %d\n" % points.points
        blob += "Status: %s\n\n" % ("<green>Open<end>" if points.disabled == 0 else "<red>Disabled<end>")

        blob += "<header2>Account log<end>\n"
        if points_log is None:
            blob += "No entries in log."
        else:
            for entry in points_log:
                name_reference = "<yellow>%s's<end>" % char if char != request.sender.name else "your"

                if entry.audit == 0:
                    # If points is 0, then it's a general case log
                    blob += "<grey>[%s]<end> <orange>\"%s\"<end>" % (
                            self.util.format_datetime(entry.time), entry.reason)
                elif entry.audit > 0:
                    pts = "<green>%d<end>" % entry.audit
                    blob += "<grey>[%s]<end> %s points were added to %s account by <yellow>%s<end> with reason <orange>%s<end>" % (
                            self.util.format_datetime(entry.time), pts, name_reference,
                            self.character_service.resolve_char_to_name(entry.leader_id), entry.reason)
                elif entry.audit < 0:
                    pts = "<red>%d<end>" % (-1*entry.audit)
                    blob += "<grey>[%s]<end> %s points were taken from %s account by <yellow>%s<end> with reason <orange>%s<end>" % (
                            self.util.format_datetime(entry.time), pts, name_reference,
                            self.character_service.resolve_char_to_name(entry.leader_id), entry.reason)

                log_entry_link = self.text.make_chatcmd("%d" % entry.log_id,
                                                        "/tell <myname> account logentry %d" % entry.log_id)
                blob += " [%s]\n" % log_entry_link

        account_reference = "Account" if char == request.sender.name else "%s's account" % char
        return ChatBlob(account_reference, blob)

    def add_log_entry(self, char_id, leader_id, reason, amount=0):
        sql = "INSERT INTO points_log (char_id, audit, leader_id, reason, time) VALUES (?,?,?,?,?)"
        return self.db.exec(sql, [char_id, amount, leader_id, reason, int(time.time())]) > 0

    def alter_points(self, current_points, char_id, amount, leader_id, reason):
        sql = "UPDATE points SET points = points + ? WHERE char_id = ?"
        if self.db.exec(sql, [amount, char_id]) < 1:
            return False

        if not self.add_log_entry(char_id, leader_id, reason, amount):
            sql = "UPDATE points p SET p.points = ? WHERE p.char_id = ?"
            self.db.exec(sql, [current_points, char_id])
            return False

        return True
