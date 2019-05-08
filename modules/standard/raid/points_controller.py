from core.tyrbot import Tyrbot
from core.sender_obj import SenderObj
from core.db import DB
from core.decorators import command, instance, setting
from core.chat_blob import ChatBlob
from core.command_param_types import Options, Any, Int, Const, Character
from core.lookup.character_service import CharacterService
from core.setting_types import NumberSettingType
from core.setting_service import SettingService
from core.text import Text
from core.alts.alts_service import AltsService
from core.util import Util
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
        self.util: Util = registry.get_instance("util")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.alts_service: AltsService = registry.get_instance("alts_service")

    def start(self):
        if self.db.query_single("SELECT COUNT(*) AS count FROM points_presets").count < 1:
            # Populate with pre-made presets if empty
            presets = ["s13", "s28", "s35", "s42", "zodiac", "zod",
                       "tnh", "beast", "12m", "tara", "pvp", "towers",
                       "wipe", "clanwipe", "clan", "omniwipe", "omni",
                       "bonus", "early"]
            sql = "INSERT INTO points_presets (name) VALUES (?)"
            for preset in presets:
                self.db.exec(sql, [preset])

    @setting(name="initial_points_value", value="0", description="How many points new accounts start with")
    def initial_points_value(self):
        return NumberSettingType()

    @command(command="account", params=[Const("create"), Character("char")], access_level="moderator",
             description="Create a new account for given character name", sub_command="modify")
    def bank_create_cmd(self, request, _, char: SenderObj):
        alts_info = self.alts_service.get_alts(char.char_id)

        for alt in alts_info:
            sql = "SELECT char_id, disabled FROM points WHERE char_id = ? LIMIT 1"
            count = self.db.query_single(sql, [alt.char_id])

            if count:
                was_disabled = False

                if count.disabled == 1:
                    if self.db.exec("UPDATE points SET disabled = 0 WHERE char_id = ?", [alt.char_id]):
                        was_disabled = True

                if alt.char_id == char.char_id:
                    if was_disabled:
                        if self.add_log_entry(alt.char_id, request.sender.char_id,
                                              "Account was re-enabled by %s"
                                              % self.character_service.resolve_char_to_name(request.sender.char_id)):
                            return "<highlight>%s<end>'s account has been re-enabled." % char.name
                        else:
                            return "<highlight>%s<end> has an account, but failed to re-enable it." % char.name
                    else:
                        return "<highlight>%s<end> already has an account." % char.name
                else:
                    if was_disabled:
                        if self.add_log_entry(alt.char_id, request.sender.char_id,
                                              "Account was re-enabled by %s"
                                              % self.character_service.resolve_char_to_name(request.sender.char_id)):
                            return "<highlight>%s<end>'s (%s) account has been re-enabled." % (
                                char.name, self.character_service.resolve_char_to_name(alt.char_id))
                        else:
                            return "<highlight>%s<end> (%s) has an account, but failed to re-enable it." % (
                                char.name, self.character_service.resolve_char_to_name(alt.char_id))
                    else:
                        return "<highlight>%s<end> (%s) already has an account." % (
                            char.name, self.character_service.resolve_char_to_name(alt.char_id))

        main_info = alts_info.pop(0)
        changed_to_main = main_info.char_id == char.char_id

        initial_points = self.setting_service.get("initial_points_value").get_value()

        sql = "INSERT INTO points (char_id, points, created) VALUES (?,?,?)"
        if self.db.exec(sql, [main_info.char_id, initial_points, int(time.time())]) < 1:
            return "Failed to create an account for <highlight>%s<end>." % char.name

        if not self.add_log_entry(main_info.char_id, request.sender.char_id,
                                  "Account opened by %s" % request.sender.name):
            sql = "DELETE FROM points WHERE char_id = ?"
            self.db.exec(sql, [main_info.char_id])
            return "Failed to create an account for <highlight>%s<end>." % char.name

        name_reference = "%s (%s)" % (
            char.name, self.character_service.resolve_char_to_name(main_info.char_id)) if changed_to_main else char.name
        return "A new account has been created for <highlight>%s<end>." % name_reference

    @command(command="account", params=[Const("close"), Character("char")], access_level="moderator",
             description="Close the account for given character name", sub_command="modify")
    def close_account_cmd(self, request, _, char: SenderObj):
        main_id = self.alts_service.get_main(char.char_id)

        sql = "UPDATE points SET disabled = 1 WHERE char_id = ?"
        if self.db.exec(sql, [main_id.char_id]) > 0:
            reason = "Account was closed by %s" % self.character_service.resolve_char_to_name(request.sender.char_id)
            if self.add_log_entry(main_id.char_id, request.sender.char_id, reason):
                name_reference = "%s (%s)" % (char.name, self.character_service.resolve_char_to_name(
                    main_id.char_id)) if main_id.char_id != char.char_id else char.name
                return "<highlight>%s<end> has had their account disabled. Logs have been preserved." % name_reference

        return "<highlight>%s<end> does not have an open account." % char.name

    @command(command="account", params=[], access_level="all",
             description="Look up your account")
    def account_self_cmd(self, request):
        return self.get_account_display(request.sender)

    @command(command="account", params=[Const("logentry"), Int("log_id")], access_level="moderator",
             description="Look up specific log entry", sub_command="modify")
    def account_log_entry_cmd(self, _1, _2, log_id: int):
        log_entry = self.db.query_single("SELECT * FROM points_log WHERE log_id = ?", [log_id])

        if log_entry:
            char_name = self.character_service.resolve_char_to_name(log_entry.char_id)
            leader_name = self.character_service.resolve_char_to_name(log_entry.leader_id)

            blob = "Log entry ID: <highlight>%d<end>\n" % log_id
            blob += "Affecting account: <highlight>%s<end>\n" % char_name
            blob += "Action by: <highlight>%s<end>\n" % leader_name
            blob += "Type: <highlight>%s<end>\n" % ("Management" if log_entry.audit == 0 else "Altering of points")
            blob += "Reason: <highlight>%s<end>\n" % log_entry.reason
            action_links = None
            if log_entry.audit == 0:
                if "closed" in log_entry.reason:
                    action_links = self.text.make_chatcmd("Open the account",
                                                          "/tell <myname> account create %s" % char_name)
                elif "re-enabled" in log_entry.reason:
                    action_links = self.text.make_chatcmd("Close the account",
                                                          "/tell <myname> account close %s" % char_name)
            else:
                if log_entry.audit < 0:
                    reason = "Points from event (%d) has been retracted, %d points have been added." \
                             % (log_id, (-1*log_entry.audit))
                    action_links = self.text.make_chatcmd("Retract", "/tell <myname> bank give %d %s %s"
                                                          % ((-1*log_entry.audit), char_name, reason))
                else:
                    reason = "Points from event (%d) has been retracted, %d points have been deducted." \
                             % (log_id, log_entry.audit)
                    action_links = self.text.make_chatcmd("Retract", "/tell <myname> bank take %d %s %s"
                                                          % (log_entry.audit, char_name, reason))

            blob += "Actions available: [%s]\n" % (action_links if action_links is not None else "No actions available")

            return ChatBlob("Log entry (%d)" % log_id, blob)

        return "No log entry with given ID <highlight>%d<end>." % log_id

    @command(command="account", params=[Options(["give", "take"]), Int("amount"), Character("char"), Any("reason")], access_level="moderator",
             description="Give or take points from character account", sub_command="modify")
    def account_give_take_cmd(self, request, action: str, amount: int, char: SenderObj, reason: str):
        main_id = self.alts_service.get_main(char.char_id)

        sql = "SELECT * FROM points WHERE char_id = ?"
        points = self.db.query_single(sql, [main_id.char_id])

        if points:
            if points.disabled == 1:
                return "<highlight>%s<end>'s account is disabled, altering the account is not possible." % char.name

            if points.points == 0 and action == "take":
                return "<highlight>%s<end> has 0 points - can't have less than 0 points." % char.name

            if amount > points.points and action == "take":
                amount = points.points

            new_points = amount if action == "give" else 0 - amount

            if not self.alter_points(points.points, main_id.char_id, new_points, request.sender.char_id, reason):
                return "Failed to alter <highlight>%s<end>'s account." % char.name

            action = "taken from" if action == "take" else "added to"
            return "<highlight>%s<end> has had <highlight>%d<end> points %s their account." % (char.name, amount, action)

        return "<highlight>%s<end> does not have an account." % char.name

    @command(command="account", params=[Character("char")], access_level="moderator",
             description="Look up account of another char", sub_command="modify")
    def account_other_cmd(self, request, char: SenderObj):
        return self.get_account_display(char)

    @command(command="presets", params=[Const("add"), Any("name"), Int("points")], access_level="admin",
             description="Add new points preset")
    def presets_add_cmd(self, _1, _2, name: str, points: int):
        count = self.db.query_single("SELECT COUNT(*) AS count FROM points_presets WHERE name = ?", [name]).count

        if count > 0:
            return "A preset already exists with the name <highlight>%s<end>." % name

        sql = "INSERT INTO points_presets (name, points) VALUES (?,?)"
        if self.db.exec(sql, [name, points]) > 0:
            return "A preset with the name <highlight>%s<end> was added, worth <green>%d<end> points." % (name, points)

        return "Failed to insert new preset in DB."

    @command(command="presets", params=[Const("rem"), Int("preset_id")], access_level="admin",
             description="Delete preset")
    def presets_rem_cmd(self, _1, _2, preset_id: int):
        if self.db.exec("DELETE FROM points_presets WHERE preset_id = ?", [preset_id]) > 0:
            return "Successfully removed preset with ID <highlight>%d<end>." % preset_id

        return "No preset with given ID <highlight>%d<end>." % preset_id

    @command(command="presets", params=[Const("alter"), Int("preset_id"), Int("new_points")], access_level="admin",
             description="Alter the points dished out by given preset")
    def presets_alter_cmd(self, _1, _2, preset_id: int, new_points: int):
        preset = self.db.query_single("SELECT * FROM points_presets WHERE preset_id = ?", [preset_id])

        if preset:
            if self.db.exec("UPDATE points_presets SET points = ? WHERE preset_id = ?", [new_points, preset_id]) > 0:
                return "Successfully updated the preset, <highlight>%s<end>, to dish out " \
                       "<green>%d<end> points instead of <red>%d<end>." % (preset.name, new_points, preset.points)

            return "Failed to update preset with ID <highlight>%d<end>." % preset_id

    @command(command="presets", params=[], access_level="admin",
             description="See list of points presets")
    def presets_cmd(self, _):
        return ChatBlob("Points presets", self.build_preset_list())

    def build_preset_list(self):
        presets = self.db.query("SELECT * FROM points_presets ORDER BY name ASC, points DESC")

        if presets:
            blob = ""

            for preset in presets:
                add_points_link = self.text.make_chatcmd("Add pts", "/tell <myname> raid addpts %s" % preset.name)
                delete_link = self.text.make_chatcmd("Delete", "/tell <myname> presets rem %d" % preset.preset_id)
                blob += "<highlight>%s<end> worth <green>%d<end> points [id: %d]\n | [%s] [%s]\n\n" \
                        % (preset.name, preset.points, preset.preset_id, add_points_link, delete_link)

            return blob

        return "No presets available. To add new presets use <highlight><symbol>presets add preset_name preset_points<end>."

    def add_log_entry(self, char_id: int, leader_id: int, reason: str, amount=0):
        sql = "INSERT INTO points_log (char_id, audit, leader_id, reason, time) VALUES (?,?,?,?,?)"
        return self.db.exec(sql, [char_id, amount, leader_id, reason, int(time.time())]) > 0

    def alter_points(self, current_points: int, char_id: int, amount: int, leader_id: int, reason: str):
        sql = "UPDATE points SET points = points + ? WHERE char_id = ?"
        if self.db.exec(sql, [amount, char_id]) < 1:
            return False

        if not self.add_log_entry(char_id, leader_id, reason, amount):
            sql = "UPDATE points p SET p.points = ? WHERE p.char_id = ?"
            self.db.exec(sql, [current_points, char_id])
            return False

        return True

    def get_account_display(self, char: SenderObj):
        main = self.alts_service.get_main(char.char_id)
        if not main:
            return "Could not find character <highlight>%s<end>." % char.name

        points_log = self.db.query("SELECT * FROM points_log WHERE char_id = ? ORDER BY time DESC LIMIT 50",
                                   [main.char_id])
        points = self.db.query_single("SELECT points, disabled FROM points WHERE char_id = ?", [main.char_id])
        if not points:
            return "Could not find raid account for <highlight>%s<end>." % char.name

        alts_link = self.text.make_chatcmd("Alts", "/tell <myname> alts %s" % main.name)
        blob = ""
        blob += "Holder of account: %s [%s]\n" % (main.name, alts_link)
        blob += "Points: %d\n" % points.points
        blob += "Status: %s\n\n" % ("<green>Open<end>" if points.disabled == 0 else "<red>Disabled<end>")

        blob += "<header2>Account log<end>\n"
        if points_log is None:
            blob += "No entries in log."
        else:
            for entry in points_log:
                name_reference = "<highlight>%s<end>" % char.name

                if entry.audit == 0:
                    # If points is 0, then it's a general case log
                    blob += "<grey>[%s]<end> <orange>\"%s\"<end>" % (
                        self.util.format_datetime(entry.time), entry.reason)
                elif entry.audit > 0:
                    pts = "<green>%d<end>" % entry.audit
                    blob += "<grey>[%s]<end> %s points were added to %s account " \
                            "by <highlight>%s<end> with reason <orange>%s<end>" \
                            % (self.util.format_datetime(entry.time),
                               pts, name_reference,
                               self.character_service.resolve_char_to_name(entry.leader_id), entry.reason)
                elif entry.audit < 0:
                    pts = "<red>%d<end>" % (-1 * entry.audit)
                    blob += "<grey>[%s]<end> %s points were taken from %s account " \
                            "by <highlight>%s<end> with reason <orange>%s<end>" \
                            % (self.util.format_datetime(entry.time),
                               pts, name_reference,
                               self.character_service.resolve_char_to_name(entry.leader_id),
                               entry.reason)

                log_entry_link = self.text.make_chatcmd("%d" % entry.log_id,
                                                        "/tell <myname> account logentry %d" % entry.log_id)
                blob += " [%s]\n" % log_entry_link

        return ChatBlob("%s Account" % char.name, blob)
