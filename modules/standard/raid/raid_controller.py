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


@instance()
class RaidController:
    MESSAGE_SOURCE = "raid"
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
        self.message_hub_service = registry.get_instance("message_hub_service")
        self.leader_controller = registry.get_instance("leader_controller")
        self.topic_controller = registry.get_instance("topic_controller")

    def pre_start(self):
        self.message_hub_service.register_message_source(self.MESSAGE_SOURCE)

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS raid_log (raid_id INT PRIMARY KEY AUTO_INCREMENT, raid_name VARCHAR(255) NOT NULL, "
                     "started_by BIGINT NOT NULL, raid_start INT NOT NULL, raid_end INT NOT NULL)")
        self.db.exec("CREATE TABLE IF NOT EXISTS raid_log_participants (raid_id INT NOT NULL, raider_id BIGINT NOT NULL, "
                     "accumulated_points INT DEFAULT 0, left_raid INT, was_kicked INT, was_kicked_reason VARCHAR(500))")

        self.db.load_sql_file(self.module_dir + "/" + "raid_loot.sql")

    @command(command="raid", params=[], access_level="member",
             description="Show the current raid status")
    def raid_cmd(self, request):
        if not self.raid:
            return self.NO_RAID_RUNNING_RESPONSE

        t = int(time.time())

        blob = ""
        blob += "Name: <highlight>%s</highlight>\n" % self.raid.raid_name
        blob += "Started By: <highlight>%s</highlight>\n" % self.raid.started_by.name
        blob += "Started At: <highlight>%s</highlight> (%s ago)\n" % (self.util.format_datetime(self.raid.started_at), self.util.time_to_readable(t - self.raid.started_at))
        blob += "Status: %s" % ("<green>Open</green>" if self.raid.is_open else "<red>Closed</red>")
        if self.raid.is_open:
            blob += " (%s)" % self.text.make_tellcmd("Join", "raid join")
        blob += "\n\n"

        topic = self.topic_controller.get_topic()
        if topic:
            time_str = self.util.time_to_readable(int(time.time()) - topic["created_at"])
            blob += "<header2>Orders</header2>\n"
            blob += "%s\n- <highlight>%s</highlight> %s ago\n\n" % (topic["topic_message"], topic["created_by"]["name"], time_str)

        blob += "<header2>Raiders</header2>\n"
        for raider in self.raid.raiders:
            if raider.is_active:
                blob += self.text.format_char_info(raider.get_active_char()) + "\n"

        return ChatBlob("Raid Status", blob)

    @command(command="raid", params=[Const("start"), Any("raid_name")],
             description="Start new raid", access_level="moderator", sub_command="manage")
    def raid_start_cmd(self, request, _, raid_name: str):
        if self.raid:
            return f"The raid <highlight>{self.raid.raid_name}</highlight> is already running."

        msg = self.leader_controller.set_raid_leader(request.sender, request.sender)
        request.reply(msg)
        if self.leader_controller.leader and self.leader_controller.leader.char_id != request.sender.char_id:
            return None

        self.raid = Raid(raid_name, request.sender)

        leader_alts = self.alts_service.get_alts(request.sender.char_id)
        self.raid.raiders.append(Raider(leader_alts, request.sender.char_id))

        join_link = self.get_raid_join_blob("Click here")

        msg = "\n<highlight>----------------------------------------</highlight>\n"
        msg += "<highlight>%s</highlight> has just started the <highlight>%s</highlight> raid.\n" % (request.sender.name, raid_name)
        msg += "%s to join\n" % join_link
        msg += "<highlight>----------------------------------------</highlight>"

        self.send_message(msg)

    @command(command="raid", params=[Const("cancel")], description="Cancel the raid without saving/logging",
             access_level="moderator", sub_command="manage")
    def raid_cancel_cmd(self, request, _):
        if self.raid is None:
            return self.NO_RAID_RUNNING_RESPONSE

        self.send_message("<highlight>%s</highlight> canceled the <highlight>%s</highlight> raid prematurely." % (request.sender.name, self.raid.raid_name))
        self.raid = None
        self.topic_controller.clear_topic()

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

                    self.send_message("%s returned to actively participating in the raid." % request.sender.name)

            elif in_raid.is_active:
                former_active_name = self.character_service.resolve_char_to_name(in_raid.active_id)
                in_raid.active_id = request.sender.char_id
                self.send_message("<highlight>%s</highlight> joined the raid with a different alt, <highlight>%s</highlight>." % (former_active_name, request.sender.name))

            elif not in_raid.is_active:
                if not self.raid.is_open:
                    return "Raid is closed."
                former_active_name = self.character_service.resolve_char_to_name(in_raid.active_id)
                in_raid.active_id = request.sender.char_id
                in_raid.was_kicked = None
                in_raid.was_kicked_reason = None
                in_raid.left_raid = None
                self.send_message("%s returned to actively participate with a different alt, <highlight>%s</highlight>." % (former_active_name, request.sender.name))

        elif self.raid.is_open:
            alts = self.alts_service.get_alts(request.sender.char_id)
            self.raid.raiders.append(Raider(alts, request.sender.char_id))
            self.send_message("<highlight>%s</highlight> joined the raid." % request.sender.name)
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
            self.send_message("<highlight>%s</highlight> left the raid." % request.sender.name)
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
            account = self.points_controller.get_account(raider.main_id)

            if raider.is_active:
                if account.disabled == 0:
                    self.points_controller.alter_points(raider.main_id, preset.points, request.sender.char_id, preset.name)
                    raider.accumulated_points += preset.points
                else:
                    self.points_controller.add_log_entry(raider.main_id, request.sender.char_id,
                                                         "Participated in raid with a disabled account, missed points from %s." % preset.name)
            else:
                self.points_controller.add_log_entry(raider.main_id, request.sender.char_id,
                                                     "Was inactive during raid, %s, when points for %s were dished out." % (self.raid.raid_name, preset.name))

        self.send_message("<highlight>%d</highlight> points added to all active raiders for <highlight>%s</highlight>." % (preset.points, preset.name))

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
                blob += "\n[<a href='chatcmd://%s'>Active check</a>]\n\n" % active_check_names
                count = 0
                raider_names.clear()

            raider_name = self.character_service.resolve_char_to_name(raider.active_id)
            akick_link = self.text.make_tellcmd("Active kick", "raid kick %s inactive" % raider_name)
            warn_link = self.text.make_chatcmd("Warn", "/tell %s You missed active check, please give notice." % raider_name)
            blob += "<highlight>%s</highlight> [%s] [%s]\n" % (raider_name, akick_link, warn_link)
            raider_names.append(raider_name)
            count += 1

        if len(raider_names) > 0:
            active_check_names = "/assist "
            active_check_names += "\\n /assist ".join(raider_names)

            blob += "\n[<a href='chatcmd://%s'>Active check</a>]\n\n" % active_check_names
            raider_names.clear()

        return ChatBlob("Active check", blob)

    @command(command="raid", params=[Const("add"), Character("char")],
             description="Add a character to the raid", access_level="moderator", sub_command="manage")
    def raid_add_cmd(self, request, _, char):
        if self.raid is None:
            return self.NO_RAID_RUNNING_RESPONSE

        alts = self.alts_service.get_alts(char.char_id)
        in_raid = self.is_in_raid(alts[0].char_id)

        if in_raid is None:
            self.raid.raiders.append(Raider(alts, char.char_id))
            self.bot.send_private_message(char.char_id, f"You have been added to the raid <highlight>{self.raid.raid_name}</highlight>.")
            return "<highlight>%s</highlight> has been added to the raid." % char.name
        else:
            if not in_raid.is_active:
                in_raid.is_active = True
                in_raid.was_kicked = None
                in_raid.was_kicked_reason = None
                in_raid.left_raid = None
                self.bot.send_private_message(char.char_id, f"You have been set as active in the raid <highlight>{self.raid.raid_name}</highlight>.")
                return f"<highlight>{char.name}</highlight> is has been set as active."
            else:
                return f"<highlight>{char.name}</highlight> is already in the raid."

    @command(command="raid", params=[Const("kick"), Character("char"), Any("reason")],
             description="Set raider as kicked with a reason", access_level="moderator", sub_command="manage")
    def raid_kick_cmd(self, request, _, char: SenderObj, reason: str):
        if self.raid is None:
            return self.NO_RAID_RUNNING_RESPONSE

        main_id = self.alts_service.get_main(char.char_id).char_id
        in_raid = self.is_in_raid(main_id)

        if in_raid is not None:
            if not in_raid.is_active:
                return "<highlight>%s</highlight> is already set as inactive." % char.name

            in_raid.is_active = False
            in_raid.was_kicked = int(time.time())
            in_raid.was_kicked_reason = reason
            self.bot.send_private_message(char.char_id,
                                          f"You have been kicked from raid <highlight>{self.raid.raid_name}</highlight> with reason <highlight>{reason}</highlight>.")
            return "<highlight>%s</highlight> has been kicked from the raid with reason <highlight>%s</highlight>." % (char.name, reason)
        else:
            return "<highlight>%s</highlight> is not participating." % char.name

    @command(command="raid", params=[Const("open")], description="Open raid for new participants",
             access_level="moderator", sub_command="manage")
    def raid_open_cmd(self, request, action):
        if not self.raid:
            return self.NO_RAID_RUNNING_RESPONSE

        if self.raid.is_open:
            return "Raid is already open."
        else:
            self.raid.is_open = True
            self.send_message("Raid has been opened by %s." % request.sender.name)

    @command(command="raid", params=[Const("close")], description="Close raid for new participants",
             access_level="moderator", sub_command="manage")
    def raid_close_cmd(self, request, action):
        if not self.raid:
            return self.NO_RAID_RUNNING_RESPONSE

        if self.raid.is_open:
            self.raid.is_open = False
            self.send_message("Raid has been closed by %s." % request.sender.name)
        else:
            return "Raid is already closed."

    @command(command="raid", params=[Options(["end", "save"])], description="End raid, and log results",
             access_level="moderator", sub_command="manage")
    def raid_save_cmd(self, request, _):
        if not self.raid:
            return self.NO_RAID_RUNNING_RESPONSE

        sql = "INSERT INTO raid_log (raid_name, started_by, raid_start, raid_end) VALUES (?,?,?,?)"
        self.db.exec(sql, [self.raid.raid_name, self.raid.started_by.char_id, self.raid.started_at, int(time.time())])

        raid_id = self.db.query_single("SELECT raid_id FROM raid_log ORDER BY raid_id DESC LIMIT 1").raid_id

        for raider in self.raid.raiders:
            sql = "INSERT INTO raid_log_participants (raid_id, raider_id, accumulated_points, left_raid, was_kicked, was_kicked_reason) VALUES (?,?,?,?,?,?)"
            self.db.exec(sql, [raid_id, raider.active_id, raider.accumulated_points, raider.left_raid, raider.was_kicked, raider.was_kicked_reason])

        self.raid = None
        self.topic_controller.clear_topic()

        self.send_message("Raid saved and ended.")

    @command(command="raid", params=[Const("history"), Int("raid_id")],
             description="Show log entry for raid",
             access_level="moderator", sub_command="manage")
    def raid_history_detail_cmd(self, request, _, raid_id: int):
        sql = "SELECT r.*, p.*, p2.name AS raider_name FROM raid_log r " \
              "LEFT JOIN raid_log_participants p ON r.raid_id = p.raid_id " \
              "LEFT JOIN player p2 ON p.raider_id = p2.char_id " \
              "WHERE r.raid_id = ? ORDER BY p.accumulated_points DESC"
        log_entry = self.db.query(sql, [raid_id])
        pts_sum = self.db.query_single("SELECT SUM(p.accumulated_points) AS sum FROM raid_log_participants p WHERE p.raid_id = ?", [raid_id]).sum

        if not log_entry:
            return "No such log entry."

        blob = "Raid name: <highlight>%s</highlight>\n" % log_entry[0].raid_name
        blob += "Started by: <highlight>%s</highlight>\n" % self.character_service.resolve_char_to_name(log_entry[0].started_by)
        blob += "Start time: <highlight>%s</highlight>\n" % self.util.format_datetime(log_entry[0].raid_start)
        blob += "End time: <highlight>%s</highlight>\n" % self.util.format_datetime(log_entry[0].raid_end)
        blob += "Run time: <highlight>%s</highlight>\n" % self.util.time_to_readable(log_entry[0].raid_end - log_entry[0].raid_start)
        blob += "Total points: <highlight>%d</highlight>\n\n" % pts_sum

        blob += "<header2>Participants</header2>\n"
        for raider in log_entry:
            main_info = self.alts_service.get_main(raider.raider_id)
            if main_info.char_id != raider.raider_id:
                alt_link_text = "Alt of %s" % main_info.name
            else:
                alt_link_text = "Alts"
            alt_link = self.text.make_tellcmd(alt_link_text, "alts %s" % raider.raider_name)
            account_link = self.text.make_tellcmd("Account", "account %s" % raider.raider_name)
            blob += "%s - %d points earned [%s] [%s]\n" % (raider.raider_name, raider.accumulated_points, account_link, alt_link)

            if raider.left_raid:
                blob += "Left raid: %s\n" % self.util.format_datetime(raider.left_raid)

            if raider.was_kicked:
                blob += "Was kicked: %s\n" % self.util.format_datetime(raider.was_kicked)

            if raider.was_kicked_reason:
                blob += "Kick reason: %s\n" % raider.was_kicked_reason

            blob += "\n"

        return ChatBlob("Raid: %s" % log_entry[0].raid_name, blob)

    @command(command="raid", params=[Const("history")], description="Show a list of recent raids",
             access_level="member")
    def raid_history_cmd(self, request, _):
        sql = "SELECT * FROM raid_log ORDER BY raid_end DESC LIMIT 30"
        raids = self.db.query(sql)

        blob = ""
        for raid in raids:
            participant_link = self.text.make_tellcmd("Detail", "raid history %d" % raid.raid_id)
            timestamp = self.util.format_datetime(raid.raid_start)
            leader_name = self.character_service.resolve_char_to_name(raid.started_by)
            blob += "[%d] [%s] <highlight>%s</highlight> started by <highlight>%s</highlight> [%s]\n" % (raid.raid_id, timestamp, raid.raid_name, leader_name, participant_link)

        return ChatBlob("Raid History (%d)" % len(raids), blob)

    def is_in_raid(self, main_id: int):
        if self.raid is None:
            return None

        for raider in self.raid.raiders:
            if raider.main_id == main_id:
                return raider

    def get_raid_join_blob(self, link_txt: str):
        blob = "<header2>1. Join the raid</header2>\n" \
               "To join the current raid <highlight>%s</highlight>, send the following tell to <myname>\n" \
               "<tab><tab><a href='chatcmd:///tell <myname> <symbol>raid join'>/tell <myname> raid " \
               "join</a>\n\n<header2>2. Enable LFT</header2>\nWhen you have joined the raid, go lft " \
               "with \"<myname>\" as description\n<tab><tab><a href='chatcmd:///lft <myname>'>/lft <myname></a>\n\n" \
               "<header2>3. Announce</header2>\nYou could announce to the raid leader, that you have enabled " \
               "LFT\n<tab><tab><a href='chatcmd:///group <myname> I am on lft'>Announce</a> that you have enabled " \
               "lft\n\n<header2>4. Rally with yer mateys</header2>\nFinally, move towards the starting location of " \
               "the raid.\n<highlight>Ask for help</highlight> if you're in doubt of where to go." % self.raid.raid_name

        return self.text.paginate_single(ChatBlob(link_txt, blob))

    def send_message(self, msg):
        self.message_hub_service.send_message(self.MESSAGE_SOURCE, None, None, msg)
