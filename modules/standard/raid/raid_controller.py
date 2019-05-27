import time

from core.alts.alts_service import AltsService
from core.chat_blob import ChatBlob
from core.command_param_types import Const, Int, Any, Options, Character
from core.db import DB
from core.decorators import instance, command
from core.lookup.character_service import CharacterService
from core.sender_obj import SenderObj
from core.setting_service import SettingService
from core.text import Text
from core.tyrbot import Tyrbot
from core.util import Util
from .points_controller import PointsController


class Raider:
    def __init__(self, alts, active):
        self.main_id = alts[0].char_id
        self.alts = alts
        self.active_id = active
        self.accumulated_points = 0
        self.is_active = True
        self.left_raid = None
        self.was_kicked = None
        self.was_kicked_reason = None

    def get_active_char(self):
        for alt in self.alts:
            if self.active_id == alt.char_id:
                return alt
        return None


class Raid:
    def __init__(self, raid_name, started_by, raiders=None):
        self.raid_name = raid_name
        self.started_at = int(time.time())
        self.started_by = started_by
        self.raiders = raiders or []
        self.is_open = True
        self.raid_orders = None


@instance()
class RaidController:
    NO_RAID_RUNNING_RESPONSE = "No raid is running."

    def __init__(self):
        self.raid = None

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.alts_service: AltsService = registry.get_instance("alts_service")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.points_controller: PointsController = registry.get_instance("points_controller")
        self.util: Util = registry.get_instance("util")

    @command(command="raid", params=[], access_level="member",
             description="Show the current raid status")
    def raid_cmd(self, request):
        if not self.raid:
            return self.NO_RAID_RUNNING_RESPONSE

        t = int(time.time())

        blob = ""
        blob += "Name: <highlight>%s<end>\n" % self.raid.raid_name
        blob += "Started By: <highlight>%s<end>\n" % self.raid.started_by.name
        blob += "Started At: <highlight>%s<end> (%s ago)\n" % (self.util.format_datetime(self.raid.started_at), self.util.time_to_readable(t - self.raid.started_at))
        blob += "Status: %s" % ("<green>Open<end>" if self.raid.is_open else "<red>Closed<end>")
        if self.raid.is_open:
            blob += " (%s)" % self.text.make_chatcmd("Join", "/tell <myname> raid join")
        blob += "\n\n"
        if self.raid.raid_orders:
            blob += "<header2>Orders<end>\n"
            blob += self.raid.raid_orders + "\n\n"
        blob += "<header2>Raiders<end>\n"
        for raider in self.raid.raiders:
            if raider.is_active:
                blob += self.text.format_char_info(raider.get_active_char()) + "\n"

        return ChatBlob("Raid Status", blob)

    @command(command="raid", params=[Const("start"), Any("raid_name")],
             description="Start new raid", access_level="moderator", sub_command="manage")
    def raid_start_cmd(self, request, _, raid_name: str):
        if self.raid:
            return "The <highlight>%s<end> raid is already running." % self.raid.raid_name

        self.raid = Raid(raid_name, request.sender)

        leader_alts = self.alts_service.get_alts(request.sender.char_id)
        self.raid.raiders.append(Raider(leader_alts, request.sender.char_id))

        join_link = self.get_raid_join_blob("Click here")

        msg = "\n<highlight>----------------------------------------<end>\n"
        msg += "<highlight>%s<end> has just started the <highlight>%s<end> raid.\n" % (request.sender.name, raid_name)
        msg += "%s to join\n" % join_link
        msg += "<highlight>----------------------------------------<end>"

        self.bot.send_org_message(msg)
        self.bot.send_private_channel_message(msg)

    @command(command="raid", params=[Options(["end", "cancel"])], description="End raid without saving/logging.",
             access_level="moderator", sub_command="manage")
    def raid_cancel_cmd(self, request, _):
        if self.raid is None:
            return self.NO_RAID_RUNNING_RESPONSE

        raid_name = self.raid.raid_name
        self.raid = None
        self.bot.send_org_message("<highlight>%s<end> canceled the <highlight>%s<end> raid prematurely." % (request.sender.name, raid_name))
        self.bot.send_private_channel_message("<highlight>%s<end> canceled the <highlight>%s<end> raid prematurely." % (request.sender.name, raid_name))

    @command(command="raid", params=[Const("join")], description="Join the ongoing raid", access_level="member")
    def raid_join_cmd(self, request, _):
        if not self.raid:
            return self.NO_RAID_RUNNING_RESPONSE

        main_id = self.alts_service.get_main(request.sender.char_id).char_id
        in_raid = self.is_in_raid(main_id)

        if in_raid is not None:
            if in_raid.active_id == request.sender.char_id:
                if in_raid.is_active:
                    return "You are already participating in the raid."
                else:
                    if not self.raid.is_open:
                        return "Raid is closed."
                    in_raid.is_active = True
                    in_raid.was_kicked = None
                    in_raid.was_kicked_reason = None
                    in_raid.left_raid = None
                    self.bot.send_private_channel_message("%s returned to actively participating in the raid." % request.sender.name)
                    self.bot.send_org_message("%s returned to actively participating in the raid." % request.sender.name)

            elif in_raid.is_active:
                former_active_name = self.character_service.resolve_char_to_name(in_raid.active_id)
                in_raid.active_id = request.sender.char_id
                self.bot.send_private_channel_message("<highlight>%s<end> joined the raid with a different alt, <highlight>%s<end>." % (former_active_name, request.sender.name))
                self.bot.send_org_message("<highlight>%s<end> joined the raid with a different alt, <highlight>%s<end>." % (former_active_name, request.sender.name))

            elif not in_raid.is_active:
                if not self.raid.is_open:
                    return "Raid is closed."
                former_active_name = self.character_service.resolve_char_to_name(in_raid.active_id)
                in_raid.active_id = request.sender.char_id
                in_raid.was_kicked = None
                in_raid.was_kicked_reason = None
                in_raid.left_raid = None
                self.bot.send_private_channel_message("%s returned to actively participate with a different alt, <highlight>%s<end>." % (former_active_name, request.sender.name))
                self.bot.send_org_message("%s returned to actively participate with a different alt, <highlight>%s<end>." % (former_active_name, request.sender.name))

        elif self.raid.is_open:
            alts = self.alts_service.get_alts(request.sender.char_id)
            self.raid.raiders.append(Raider(alts, request.sender.char_id))
            self.bot.send_private_channel_message("<highlight>%s<end> joined the raid." % request.sender.name)
            self.bot.send_org_message("<highlight>%s<end> joined the raid." % request.sender.name)
        else:
            return "Raid is closed."

    @command(command="raid", params=[Const("leave")], description="Leave the ongoing raid", access_level="member")
    def raid_leave_cmd(self, request, _):
        in_raid = self.is_in_raid(self.alts_service.get_main(request.sender.char_id).char_id)
        if in_raid:
            if not in_raid.is_active:
                return "You are not active in the raid."

            in_raid.is_active = False
            in_raid.left_raid = int(time.time())
            self.bot.send_private_channel_message("<highlight>%s<end> left the raid." % request.sender.name)
            self.bot.send_org_message("<highlight>%s<end> left the raid." % request.sender.name)
        else:
            return "You are not in the raid."

    @command(command="raid", params=[Const("addpts"), Any("name")], description="Add points to all active participants",
             access_level="moderator", sub_command="manage")
    def points_add_cmd(self, request, _, name: str):
        if not self.raid:
            return self.NO_RAID_RUNNING_RESPONSE

        preset = self.db.query_single("SELECT * FROM points_presets WHERE name = ?", [name])
        if not preset:
            return ChatBlob("No such preset - see list of presets", self.points_controller.build_preset_list())

        for raider in self.raid.raiders:
            current_points = self.db.query_single("SELECT points, disabled FROM points WHERE char_id = ?", [raider.main_id])

            if raider.is_active:
                if current_points and current_points.disabled == 0:
                    self.points_controller.alter_points(current_points.points, raider.main_id, preset.points, request.sender.char_id, preset.name)
                    raider.accumulated_points += preset.points
                else:
                    self.points_controller.add_log_entry(raider.main_id, request.sender.char_id,
                                                         "Participated in raid without an open account, "
                                                         "missed points from %s." % preset.name)
            else:
                if current_points:
                    self.points_controller.add_log_entry(raider.main_id, request.sender.char_id,
                                                         "Was inactive during raid, %s, when points "
                                                         "for %s was dished out."
                                                         % (self.raid.raid_name, preset.name))
                else:
                    self.points_controller.add_log_entry(raider.main_id, request.sender.char_id,
                                                         "Was inactive during raid, %s, when points for %s "
                                                         "was dished out - did not have an active account at "
                                                         "the given time." % (self.raid.raid_name, preset.name))
        return "<highlight>%d<end> points added to all active raiders." % preset.points

    @command(command="raid", params=[Const("active")], description="Get a list of raiders to do active check",
             access_level="moderator", sub_command="manage")
    def raid_active_cmd(self, request, _):
        if not self.raid:
            return self.NO_RAID_RUNNING_RESPONSE

        blob = ""

        count = 0
        raider_names = []
        for raider in self.raid.raiders:
            if count == 10:
                active_check_names = "/assist "
                active_check_names += "\\n /assist ".join(raider_names)
                blob += "[<a href='chatcmd://%s'>Active check</a>]\n\n" % active_check_names
                count = 0
                raider_names.clear()

            raider_name = self.character_service.resolve_char_to_name(raider.active_id)
            akick_link = self.text.make_chatcmd("Active kick", "/tell <myname> raid kick %s inactive" % raider.main_id)
            warn_link = self.text.make_chatcmd("Warn", "/tell <myname> cmd %s missed active check, please give notice." % raider_name)
            blob += "<highlight>%s<end> [%s] [%s]\n" % (raider_name, akick_link, warn_link)
            raider_names.append(raider_name)
            count += 1

        if len(raider_names) > 0:
            active_check_names = "/assist "
            active_check_names += "\\n /assist ".join(raider_names)

            blob += "[<a href='chatcmd://%s'>Active check</a>]\n\n" % active_check_names
            raider_names.clear()

        return ChatBlob("Active check", blob)

    @command(command="raid", params=[Const("kick"), Character("char"), Any("reason")],
             description="Set raider as kicked with a reason", access_level="moderator", sub_command="manage")
    def raid_kick_cmd(self, _1, _2, char: SenderObj, reason: str):
        if self.raid is None:
            return self.NO_RAID_RUNNING_RESPONSE

        main_id = self.alts_service.get_main(char.char_id).char_id
        in_raid = self.is_in_raid(main_id)

        try:
            int(char.name)
            char.name = self.character_service.resolve_char_to_name(char.name)
        except ValueError:
            pass

        if in_raid is not None:
            if not in_raid.is_active:
                return "<highlight>%s<end> is already set as inactive." % char.name

            in_raid.is_active = False
            in_raid.was_kicked = int(time.time())
            in_raid.was_kicked_reason = reason
            return "<highlight>%s<end> has been kicked from the raid with reason \"%s\"." % (char.name, reason)
        else:
            return "<highlight>%s<end> is not participating." % char.name

    @command(command="raid", params=[Options(["open", "close"])], description="Open/close raid for new participants",
             access_level="moderator", sub_command="manage")
    def raid_open_close_cmd(self, request, action):
        if not self.raid:
            return self.NO_RAID_RUNNING_RESPONSE

        if action == "open":
            if self.raid.is_open:
                return "Raid is already open."
            self.raid.is_open = True
            self.bot.send_private_channel_message("Raid has been opened by %s." % request.sender.name)
            self.bot.send_org_message("Raid has been opened by %s." % request.sender.name)
            return
        elif action == "close":
            if self.raid.is_open:
                self.raid.is_open = False
                self.bot.send_private_channel_message("Raid has been closed by %s." % request.sender.name)
                self.bot.send_org_message("Raid has been closed by %s." % request.sender.name)
                return
            return "Raid is already closed."

    @command(command="raid", params=[Const("save")], description="Save and log running raid", access_level="moderator", sub_command="manage")
    def raid_save_cmd(self, _1, _2):
        if not self.raid:
            return self.NO_RAID_RUNNING_RESPONSE

        sql = "INSERT INTO raid_log (raid_name, started_by, raid_start, raid_end) VALUES (?,?,?,?)"
        num_rows = self.db.exec(sql, [self.raid.raid_name, self.raid.started_by.char_id, self.raid.started_at, int(time.time())])
        if num_rows > 0:
            raid_id = self.db.query_single("SELECT raid_id FROM raid_log ORDER BY raid_id DESC LIMIT 1").raid_id

            for raider in self.raid.raiders:
                sql = "INSERT INTO raid_log_participants (raid_id, raider_id, accumulated_points, left_raid, was_kicked, was_kicked_reason) VALUES (?,?,?,?,?,?)"
                self.db.exec(sql, [raid_id, raider.active_id, raider.accumulated_points, raider.left_raid, raider.was_kicked, raider.was_kicked_reason])

            self.raid = None

            return "Raid saved."
        else:
            return "Failed to log raid. Try again or cancel raid to end raid."

    @command(command="raid", params=[Const("logentry"), Int("raid_id"), Character("char", is_optional=True)],
             description="Show log entry for raid, with possibility of narrowing down the log for character in raid",
             access_level="moderator", sub_command="manage")
    def raid_log_entry_cmd(self, _1, _2, raid_id: int, char: SenderObj):
        log_entry_spec = None
        if char:
            sql = "SELECT * FROM raid_log r LEFT JOIN raid_log_participants p ON r.raid_id = p.raid_id WHERE r.raid_id = ? AND p.raider_id = ?"
            log_entry_spec = self.db.query_single(sql, [raid_id, char.char_id])

        sql = "SELECT * FROM raid_log r LEFT JOIN raid_log_participants p ON r.raid_id = p.raid_id WHERE r.raid_id = ? ORDER BY p.accumulated_points DESC"
        log_entry = self.db.query(sql, [raid_id])
        pts_sum = self.db.query_single("SELECT SUM(p.accumulated_points) AS sum FROM raid_log_participants p WHERE p.raid_id = ?", [raid_id]).sum

        if not log_entry:
            return "No such log entry."

        blob = "Raid name: <highlight>%s<end>\n" % log_entry[0].raid_name
        blob += "Started by: <highlight>%s<end>\n" % self.character_service.resolve_char_to_name(log_entry[0].started_by)
        blob += "Start time: <highlight>%s<end>\n" % self.util.format_datetime(log_entry[0].raid_start)
        blob += "End time: <highlight>%s<end>\n" % self.util.format_datetime(log_entry[0].raid_end)
        blob += "Run time: <highlight>%s<end>\n" % self.util.time_to_readable(log_entry[0].raid_end - log_entry[0].raid_start)
        blob += "Total points: <highlight>%d<end>\n\n" % pts_sum

        if char and log_entry_spec:
            raider_name = self.character_service.resolve_char_to_name(log_entry_spec.raider_id)
            main_info = self.alts_service.get_main(log_entry_spec.raider_id)
            alt_link = "Alt of %s" % main_info.name if main_info.char_id != log_entry_spec.raider_id else "Alts"
            alt_link = self.text.make_chatcmd(alt_link, "/tell <myname> alts %s" % main_info.name)
            blob += "<header2>Log entry for %s<end>\n" % raider_name
            blob += "Raider: <highlight>%s<end> [%s]\n" % (raider_name, alt_link)
            blob += "Left raid: %s\n" % ("n/a"
                                         if log_entry_spec.left_raid is None
                                         else self.util.format_datetime(log_entry_spec.left_raid))
            blob += "Was kicked: %s\n" % ("No"
                                          if log_entry_spec.was_kicked is None
                                          else "Yes [%s]" % (self.util.format_datetime(log_entry_spec.was_kicked)))
            blob += "Kick reason: %s\n\n" % ("n/a"
                                             if log_entry_spec.was_kicked_reason is None
                                             else log_entry_spec.was_kicked_reason)

        blob += "<header2>Participants<end>\n"
        for raider in log_entry:
            raider_name = self.character_service.resolve_char_to_name(raider.raider_id)
            main_info = self.alts_service.get_main(raider.raider_id)
            alt_link = "Alt of %s" % main_info.name if main_info.char_id != raider.raider_id else "Alts"
            alt_link = self.text.make_chatcmd(alt_link, "/tell <myname> alts %s" % main_info.name)
            log_link = self.text.make_chatcmd("Log", "/tell <myname> raid logentry %d %s" % (raid_id, raider_name))
            account_link = self.text.make_chatcmd("Account", "/tell <myname> account %s" % raider_name)
            blob += "%s - %d points earned [%s] [%s] [%s]\n" % (raider_name, raider.accumulated_points, log_link, account_link, alt_link)

        log_entry_reference = "the raid %s" % log_entry[0].raid_name \
            if char is None \
            else "%s in raid %s" \
                 % (self.character_service.resolve_char_to_name(char.char_id), log_entry[0].raid_name)
        return ChatBlob("Log entry for %s" % log_entry_reference, blob)

    @command(command="raid", params=[Const("history")], description="Show a list of recent raids",
             access_level="member")
    def raid_history_cmd(self, _1, _2):
        sql = "SELECT * FROM raid_log ORDER BY raid_end DESC LIMIT 30"
        raids = self.db.query(sql)

        blob = ""
        for raid in raids:
            participant_link = self.text.make_chatcmd("Log", "/tell <myname> raid logentry %d" % raid.raid_id)
            timestamp = self.util.format_datetime(raid.raid_start)
            leader_name = self.character_service.resolve_char_to_name(raid.started_by)
            blob += "[%d] [%s] <highlight>%s<end> started by <highlight>%s<end> [%s]\n" % (raid.raid_id, timestamp, raid.raid_name, leader_name, participant_link)

        return ChatBlob("Raid history", blob)

    def is_in_raid(self, main_id: int):
        if self.raid is None:
            return None

        for raider in self.raid.raiders:
            if raider.main_id == main_id:
                return raider

    def get_raid_join_blob(self, link_txt: str):
        blob = "<header2>1. Join the raid<end>\n" \
               "To join the current raid <highlight>%s<end>, send the following tell to <myname>\n" \
               "<tab><tab><a href='chatcmd:///tell <myname> <symbol>raid join'>/tell <myname> raid " \
               "join</a>\n\n<header2>2. Enable LFT<end>\nWhen you have joined the raid, go lft " \
               "with \"<myname>\" as description\n<tab><tab><a href='chatcmd:///lft <myname>'>/lft <myname></a>\n\n" \
               "<header2>3. Announce<end>\nYou could announce to the raid leader, that you have enabled " \
               "LFT\n<tab><tab><a href='chatcmd:///group <myname> I am on lft'>Announce</a> that you have enabled " \
               "lft\n\n<header2>4. Rally with yer mateys<end>\nFinally, move towards the starting location of " \
               "the raid.\n<highlight>Ask for help<end> if you're in doubt of where to go." % self.raid.raid_name

        return self.text.paginate_single(ChatBlob(link_txt, blob))
