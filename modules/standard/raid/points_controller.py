from core.sender_obj import SenderObj
from core.db import DB
from core.decorators import command, instance
from core.chat_blob import ChatBlob
from core.command_param_types import Options, Any, Int, Const, Character, NamedParameters
from core.lookup.character_service import CharacterService
from core.setting_service import SettingService
from core.text import Text
from core.alts_service import AltsService
from core.util import Util
import time


@instance()
class PointsController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.util: Util = registry.get_instance("util")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.alts_service: AltsService = registry.get_instance("alts_service")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS points (char_id INT PRIMARY KEY, points INT DEFAULT 0, created_at INT NOT NULL, "
                     "disabled SMALLINT DEFAULT 0)")
        self.db.exec("CREATE TABLE IF NOT EXISTS points_log (log_id INT PRIMARY KEY AUTO_INCREMENT, char_id INT NOT NULL, audit INT NOT NULL, "
                     "leader_id INT NOT NULL, reason VARCHAR(255), created_at INT NOT NULL)")
        self.db.exec("CREATE TABLE IF NOT EXISTS points_presets (preset_id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(50) NOT NULL, "
                     "points INT DEFAULT 1, UNIQUE(name))")

        if self.db.query_single("SELECT COUNT(*) AS count FROM points_presets").count < 1:
            # Populate with pre-made presets if empty
            presets = ["s13", "s28", "s35", "s42", "zodiac", "zod",
                       "tnh", "beast", "12m", "tara", "pvp", "towers",
                       "wipe", "clanwipe", "clan", "omniwipe", "omni",
                       "bonus", "early"]
            sql = "INSERT INTO points_presets (name) VALUES (?)"
            for preset in presets:
                self.db.exec(sql, [preset])

    @command(command="account", params=[Const("create"), Character("char")], access_level="moderator",
             description="Create a new account for given character name", sub_command="modify")
    def bank_create_cmd(self, request, _, char: SenderObj):
        alts_info = self.alts_service.get_alts(char.char_id)

        for alt in alts_info:
            sql = "SELECT char_id, disabled FROM points WHERE char_id = ? LIMIT 1"
            row = self.db.query_single(sql, [alt.char_id])

            if row:
                was_disabled = False

                if row.disabled == 1:
                    if self.db.exec("UPDATE points SET disabled = 0 WHERE char_id = ?", [alt.char_id]):
                        was_disabled = True

                if alt.char_id == char.char_id:
                    if was_disabled:
                        self.add_log_entry(alt.char_id, request.sender.char_id, "Account was re-enabled by %s" % request.sender.name)
                        return "<highlight>%s</highlight>'s account has been re-enabled." % char.name
                    else:
                        return "<highlight>%s</highlight> already has an account." % char.name
                else:
                    if was_disabled:
                        self.add_log_entry(alt.char_id, request.sender.char_id, "Account was re-enabled by %s" % request.sender.name)
                        return "<highlight>%s</highlight>'s (%s) account has been re-enabled." % (char.name, alt.name)
                    else:
                        return "<highlight>%s</highlight> (%s) already has an account." % (char.name, alt.name)

        main_info = alts_info[0]
        changed_to_main = main_info.char_id == char.char_id

        self.create_account(main_info.char_id, request.sender)

        name_reference = "%s (%s)" % (char.name, main_info.name) if changed_to_main else char.name
        return "A new account has been created for <highlight>%s</highlight>." % name_reference

    @command(command="account", params=[Const("close"), Character("char")], access_level="moderator",
             description="Close the account for given character name", sub_command="modify")
    def close_account_cmd(self, request, _, char: SenderObj):
        main = self.alts_service.get_main(char.char_id)

        sql = "UPDATE points SET disabled = 1 WHERE char_id = ?"
        if self.db.exec(sql, [main.char_id]) > 0:
            reason = f"Account was closed by {request.sender.name}"
            self.add_log_entry(main.char_id, request.sender.char_id, reason)
            name_reference = "%s (%s)" % (char.name, main.name) if main.char_id != char.char_id else char.name
            return f"<highlight>{name_reference}</highlight> has had their account disabled. Logs have been preserved."
        else:
            return "<highlight>%s</highlight> does not have an open account." % char.name

    @command(command="account", params=[Const("history"), Int("log_id")], access_level="moderator",
             description="Look up specific account history record", sub_command="modify")
    def account_history_cmd(self, request, _, log_id: int):
        log_entry = self.db.query_single("SELECT log_id, char_id, audit, leader_id, reason, created_at FROM points_log WHERE log_id = ?", [log_id])

        if not log_entry:
            return "No account history record with given ID <highlight>%d</highlight>." % log_id

        char_name = self.character_service.resolve_char_to_name(log_entry.char_id)
        leader_name = self.character_service.resolve_char_to_name(log_entry.leader_id)

        blob = f"ID: <highlight>{log_entry.log_id}</highlight>\n"
        blob += f"Account: <highlight>{char_name}</highlight>\n"
        blob += f"Action by: <highlight>{leader_name}</highlight>\n"
        blob += "Type: <highlight>%s</highlight>\n" % ("Management" if log_entry.audit == 0 else "Altering of points")
        blob += f"Reason: <highlight>{log_entry.reason}</highlight>\n"
        blob += f"Audit: <highlight>{log_entry.audit}</highlight>\n"
        action_links = None
        if log_entry.audit == 0:
            if "closed" in log_entry.reason:
                action_links = self.text.make_tellcmd("Open the account", "account create %s" % char_name)
            elif "re-enabled" in log_entry.reason:
                action_links = self.text.make_tellcmd("Close the account", "account close %s" % char_name)
        else:
            reason = f"Points from event ({log_id}) have been retracted"
            if log_entry.audit < 0:
                action_links = self.text.make_tellcmd("Retract", f"account add {char_name} {-log_entry.audit} {reason}")
            else:
                action_links = self.text.make_tellcmd("Retract", f"account rem {char_name} {log_entry.audit} {reason}")

        blob += "Actions available: [%s]\n" % (action_links if action_links is not None else "No actions available")

        return ChatBlob(f"Account History Record ({log_id})", blob)

    @command(command="account", params=[Const("add"), Character("char"), Int("amount"), Any("reason")], access_level="moderator",
             description="Add points to an account", sub_command="modify")
    def account_add_cmd(self, request, _, char: SenderObj, amount: int, reason: str):
        main = self.alts_service.get_main(char.char_id)
        row = self.get_account(main.char_id, request.conn)

        if not row:
            return f"<highlight>{char.name}</highlight> does not have an account."

        if row.disabled == 1:
            return f"Account for <highlight>{char.name}</highlight> is disabled and cannot be altered."

        self.alter_points(main.char_id, request.sender.char_id, reason, amount)

        return f"<highlight>{char.name}</highlight> has had <highlight>{amount}</highlight> points added to their account."

    @command(command="account", params=[Options(["rem", "remove"]), Character("char"), Int("amount"), Any("reason")], access_level="moderator",
             description="Remove points from an account", sub_command="modify")
    def account_remove_cmd(self, request, _, char: SenderObj, amount: int, reason: str):
        main = self.alts_service.get_main(char.char_id)
        row = self.get_account(main.char_id, request.conn)

        if not row:
            return f"<highlight>{char.name}</highlight> does not have an account."

        if row.disabled == 1:
            return f"Account for <highlight>{char.name}</highlight> is disabled and cannot be altered."

        if amount > row.points:
            return f"<highlight>{char.name}</highlight> only has <highlight>{row.points}</highlight> points."

        self.alter_points(main.char_id, request.sender.char_id, reason, -amount)

        return f"<highlight>{char.name}</highlight> has had <highlight>{amount}</highlight> points removed from their account."

    @command(command="account", params=[NamedParameters(["page"])], access_level="all",
             description="Look up your account")
    def account_self_cmd(self, request, named_params):
        return self.get_account_display(request.sender, named_params.page)

    @command(command="account", params=[Character("char"), NamedParameters(["page"])], access_level="moderator",
             description="Look up account of another char", sub_command="modify")
    def account_other_cmd(self, request, char: SenderObj, named_params):
        return self.get_account_display(char, named_params.page)

    @command(command="raid", params=[Const("presets"), Const("add"), Any("name"), Int("points")], access_level="admin",
             description="Add new points preset", sub_command="manage_points")
    def presets_add_cmd(self, request, _1, _2, name: str, points: int):
        count = self.db.query_single("SELECT COUNT(*) AS count FROM points_presets WHERE name = ?", [name]).count

        if count > 0:
            return "A preset already exists with the name <highlight>%s</highlight>." % name

        sql = "INSERT INTO points_presets (name, points) VALUES (?,?)"
        self.db.exec(sql, [name, points])
        return "A preset with the name <highlight>%s</highlight> was added, worth <green>%d</green> points." % (name, points)

    @command(command="raid", params=[Const("presets"), Const("rem"), Int("preset_id")], access_level="admin",
             description="Delete preset", sub_command="manage_points")
    def presets_rem_cmd(self, request, _1, _2, preset_id: int):
        if self.db.exec("DELETE FROM points_presets WHERE preset_id = ?", [preset_id]) > 0:
            return "Successfully removed preset with ID <highlight>%d</highlight>." % preset_id
        else:
            return "No preset with given ID <highlight>%d</highlight>." % preset_id

    @command(command="raid", params=[Const("presets"), Const("alter"), Int("preset_id"), Int("new_points")], access_level="admin",
             description="Alter the points dished out by given preset", sub_command="manage_points")
    def presets_alter_cmd(self, request, _1, _2, preset_id: int, new_points: int):
        preset = self.db.query_single("SELECT * FROM points_presets WHERE preset_id = ?", [preset_id])

        if not preset:
            return f"Preset with ID <highlight>{preset_id}</highlight> does not exist."

        self.db.exec("UPDATE points_presets SET points = ? WHERE preset_id = ?", [new_points, preset_id])
        return "Successfully updated the preset, <highlight>%s</highlight>, to dish out " \
               "<green>%d</green> points instead of <red>%d</red>." % (preset.name, new_points, preset.points)

    @command(command="raid", params=[Options(["presets", "addpts"])], access_level="member",
             description="See list of points presets")
    def presets_cmd(self, request, _):
        return ChatBlob("Raid Points Presets", self.build_preset_list())

    def build_preset_list(self):
        presets = self.db.query("SELECT * FROM points_presets ORDER BY name ASC, points DESC")

        if presets:
            blob = ""

            for preset in presets:
                add_points_link = self.text.make_tellcmd("Add pts", "raid addpts %s" % preset.name)
                blob += "<highlight>%s</highlight> worth <green>%d</green> points %s [id: %d]\n\n" \
                        % (preset.name, preset.points, add_points_link, preset.preset_id)

            return blob

        return "No presets available. To add new presets use <highlight><symbol>presets add preset_name preset_points</highlight>."

    def add_log_entry(self, char_id: int, leader_id: int, reason: str, amount=0):
        sql = "INSERT INTO points_log (char_id, audit, leader_id, reason, created_at) VALUES (?,?,?,?,?)"
        return self.db.exec(sql, [char_id, amount, leader_id, reason, int(time.time())])

    def alter_points(self, char_id: int, leader_id: int, reason: str, amount: int):
        sql = "UPDATE points SET points = points + ? WHERE char_id = ?"
        self.db.exec(sql, [amount, char_id])

        self.add_log_entry(char_id, leader_id, reason, amount)

    def get_account(self, main_id, conn):
        sql = "SELECT p.char_id, p.points, p.disabled FROM points p WHERE p.char_id = ?"
        row = self.db.query_single(sql, [main_id])
        if not row:
            self.create_account(main_id, SenderObj(conn.get_char_id(),
                                                   conn.get_char_name(),
                                                   None))
            row = self.db.query_single(sql, [main_id])

        return row

    def create_account(self, main_id, sender):
        sql = "INSERT INTO points (char_id, points, created_at) VALUES (?,?,?)"
        self.db.exec(sql, [main_id, 0, int(time.time())])

        self.add_log_entry(main_id, sender.char_id, "Account opened by %s" % sender.name)

    def get_account_display(self, char: SenderObj, page):
        main = self.alts_service.get_main(char.char_id)
        if not main:
            return "Could not find character <highlight>%s</highlight>." % char.name

        page = int(page) if page else 1
        page_size = 20
        offset = (page - 1) * page_size

        points = self.db.query_single("SELECT points, disabled FROM points WHERE char_id = ?", [main.char_id])
        if not points:
            return "Could not find raid account for <highlight>%s</highlight>." % char.name

        alts_link = self.text.make_tellcmd("Alts", "alts %s" % main.name)
        blob = ""
        blob += "Account: %s [%s]\n" % (main.name, alts_link)
        blob += "Points: %d\n" % points.points
        blob += "Status: %s\n\n" % ("<green>Open</green>" if points.disabled == 0 else "<red>Disabled</red>")

        points_log = self.db.query("SELECT * FROM points_log WHERE char_id = ? ORDER BY created_at DESC LIMIT ?, ?",
                                   [main.char_id, offset, page_size])
        blob += "<header2>Account log</header2>\n"
        if points_log is None:
            blob += "No entries in log."
        else:
            for entry in points_log:
                if entry.audit > 0:
                    pts = "<green>+%d</green>" % entry.audit
                    blob += "<grey>[%s]</grey> %s points by <highlight>%s</highlight>; <orange>%s</orange>" \
                            % (self.util.format_datetime(entry.created_at), pts,
                               self.character_service.resolve_char_to_name(entry.leader_id), entry.reason)
                elif entry.audit < 0:
                    pts = "<red>-%d</red>" % (-1 * entry.audit)
                    blob += "<grey>[%s]</grey> %s points by <highlight>%s</highlight>; <orange>%s</orange>" \
                            % (self.util.format_datetime(entry.created_at), pts,
                               self.character_service.resolve_char_to_name(entry.leader_id),
                               entry.reason)
                else:
                    # If points is 0, then it's a general case log
                    blob += "<grey>[%s]</grey> <orange>%s</orange>" % (self.util.format_datetime(entry.created_at), entry.reason)

                log_entry_link = self.text.make_tellcmd(entry.log_id, f"account history {entry.log_id}")
                blob += " [%s]\n" % log_entry_link

        return ChatBlob("%s Account" % char.name, blob)
