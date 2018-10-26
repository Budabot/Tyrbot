from core.access_service import AccessService
from core.chat_blob import ChatBlob
from core.command_param_types import Const, Int, Item, Any, Options, Character
from core.db import DB
from core.sender_obj import SenderObj
from core.setting_types import NumberSettingType
from core.setting_service import SettingService
from core.decorators import instance, command, timerevent, setting
from core.text import Text
from core.tyrbot import Tyrbot
from core.util import Util
from core.lookup.character_service import CharacterService
from core.alts.alts_service import AltsService
from .leader_controller import LeaderController
from .points_controller import PointsController
from .item_types import LootItem, AuctionItem
from collections import OrderedDict
import secrets
import time


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


class Raid:
    def __init__(self, raid_name, started_by, raid_min_lvl, raid_limit=None, raiders=None):
        self.raid_name = raid_name
        self.started = int(time.time())
        self.started_by = started_by
        self.raid_min_lvl = raid_min_lvl
        self.raid_limit = raid_limit
        self.raiders = raiders or []
        self.is_open = True
        self.raid_orders = None


@instance()
class RaidController:
    def __init__(self):
        self.loot_list = OrderedDict()
        self.last_modify = None
        self.raid = None

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.leader_controller: LeaderController = registry.get_instance("leader_controller")
        self.access_service: AccessService = registry.get_instance("access_service")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.alts_service: AltsService = registry.get_instance("alts_service")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.points_controller: PointsController = registry.get_instance("points_controller")
        self.util: Util = registry.get_instance("util")

    @setting(name="default_min_lvl", value="1", description="Default minimum level for joining raids")
    def default_min_lvl(self):
        return NumberSettingType()

    @command(command="loot", params=[], description="Show the list of added items", access_level="all")
    def loot_cmd(self, request):
        if not self.loot_list:
            return "Loot list is empty."

        if isinstance(list(self.loot_list.values())[0], AuctionItem):
            return self.get_auction_list()
        if isinstance(list(self.loot_list.values())[0], LootItem):
            return self.get_loot_list()

        return "Error when generating list (loot type is unsupported)."

    @command(command="loot", params=[Const("clear")], description="Clear all loot", access_level="all")
    def loot_clear_cmd(self, request, _):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return "You're not set as leader, and don't have sufficient access level to override leadership."

        if self.loot_list:
            self.loot_list.clear()
            self.last_modify = None
            return "Loot list cleared."
        else:
            return "Loot list is already empty."

    @command(command="loot", params=[Const("remitem"), Int("item_index")], description="Remove existing loot",
             access_level="all")
    def loot_rem_item_cmd(self, request, _, item_index: int):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return "You're not set as leader, and don't have sufficient access level to override leadership."

        if not self.loot_list:
            return "Loot list is empty."

        try:
            if self.loot_list[item_index]:
                self.last_modify = int(time.time())
                return "Removed %s from loot list." % self.loot_list.pop(item_index).item.name
            else:
                return "Item error."
        except KeyError:
            return "Wrong index given"

    @command(command="loot", params=[Const("additem"), Item("item"), Int("item_count", is_optional=True)],
             description="Add an item to loot list", access_level="all")
    def loot_add_item_cmd(self, request, _, item, item_count: int):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return "You're not set as leader, and don't have sufficient access level to override leadership."

        if item_count is None:
            item_count = 1

        self.add_item_to_loot(item["low_id"], item["high_id"], item["ql"], item["name"], None, item_count)

        return "%s was added to loot list." % item["name"]

    @command(command="loot", params=[Const("increase"), Int("item_index")], description="Increase item count",
             access_level="all")
    def loot_increase_item_cmd(self, request, _, item_index: int):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return "You're not set as leader, and don't have sufficient access level to override leadership."

        if not self.loot_list:
            return "Loot list is empty."

        try:
            loot_item = self.loot_list[item_index]

            if loot_item:
                loot_item.count += 1
                self.last_modify = int(time.time())
                return "Increased item count for %s to %d." % (loot_item.item.name, loot_item.count)
            else:
                return "Item error."
        except KeyError:
            return "Wrong index given."

    @command(command="loot", params=[Const("decrease"), Int("item_index")], description="Decrease item count",
             access_level="all")
    def loot_decrease_item_cmd(self, request, _, item_index: int):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return "You're not set as leader, and don't have sufficient access level to override leadership."

        if not self.loot_list:
            return "Loot list is empty."

        try:
            loot_item = self.loot_list[item_index]

            if loot_item:
                loot_item.count = loot_item.count - 1 if loot_item.count > 1 else 1
                self.last_modify = int(time.time())
                return "Decreased item count for %s to %d." % (loot_item.item.name, loot_item.count)
            else:
                return "Item error."
        except KeyError:
            return "Wrong index given."

    @command(command="loot", params=[Const("add"), Int("item_index")], description="Add yourself to item",
             access_level="all")
    def loot_add_to_cmd(self, request, _, item_index: int):
        try:
            loot_item = self.loot_list[item_index]
            old_item = self.is_already_added(request.sender.name)

            if loot_item:
                if old_item is not None:
                    if old_item.item.name == loot_item.item.name:
                        name = "You have" if request.channel == "msg" else request.sender.name
                        return "%s already added to %s." % (name, loot_item.item.name)

                    old_item.bidders.remove(request.sender.name)

                name = "You have" if request.channel == "msg" else request.sender.name
                loot_item.bidders.append(request.sender.name)

                self.last_modify = int(time.time())

                return "%s moved from %s to %s." % (name, old_item.item.name, loot_item.item.name) \
                    if old_item is not None \
                    else "%s added to %s." % (name, loot_item.item.name)
            else:
                return "Item error."

        except KeyError:
            return "Wrong index given."

    @command(command="loot", params=[Const("rem")], description="Remove yourself from item", access_level="all")
    def loot_rem_from_cmd(self, request, _):
        try:
            loot_item = self.is_already_added(request.sender.name)

            if loot_item is not None:
                name = "You were" if request.channel == "msg" else "%s was" % request.sender.name
                loot_item.bidders.remove(request.sender.name)

                self.last_modify = int(time.time())

                return "%s removed from %s." % (name, loot_item.item.name)
            else:
                return "You're not added to any loot."
        except KeyError:
            return "Wrong index given."

    @command(command="loot", params=[Const("roll")], description="Roll all loot", access_level="all")
    def loot_roll_cmd(self, request, _):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return "You're not set as leader, and don't have sufficient access level to override leadership."

        if self.loot_list:
            blob = ""

            for i, loot_item in self.loot_list.items():
                winners = []

                if loot_item.bidders:
                    if len(loot_item.bidders) <= loot_item.count:
                        winners = loot_item.bidders.copy()
                        loot_item.count = loot_item.count - len(loot_item.bidders)
                        loot_item.bidders = []
                    else:
                        for j in range(0, loot_item.count):
                            winner = secrets.choice(loot_item.bidders)
                            winners.append(winner)
                            loot_item.bidders.remove(winner)
                            loot_item.count = loot_item.count - 1 if loot_item.count > 0 else 0

                    item = loot_item.item
                    blob += "%s. %s (ql%s)\n" % (i, self.text.make_item(item.low_id, item.high_id,
                                                                        item.ql, item.name), item.ql)
                    blob += " | Winners: <red>%s<end>\n\n" % '<end>, <red>'.join(winners)

            return ChatBlob("Roll results", blob) if len(blob) > 0 else "No one was added to any loot"
        else:
            return "No loot to roll."

    @command(command="loot", params=[Const("reroll")], description="Rebuild loot list", access_level="all")
    def loot_reroll_cmd(self, request, _):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return "You're not set as leader, and don't have sufficient access level to override leadership."

        if self.loot_list:
            count = 1
            for key in sorted(list(self.loot_list.keys())):
                if self.loot_list[key].count <= 0:
                    del self.loot_list[key]
                else:
                    loot_item = self.loot_list[key]
                    del self.loot_list[key]
                    self.loot_list[count] = loot_item
                    count += 1

            self.last_modify = int(time.time())

            return "List has been rebuilt." if len(self.loot_list) > 0 else "No items left to roll."
        else:
            return "Loot list is empty."

    @command(command="loot", params=[Const("additem"), Const("raid"), Int("item_id"), Int("item_count")],
             description="Used by the loot lists to add items to loot list", access_level="all")
    def loot_add_raid_item(self, request, _1, _2, item_id: int, item_count: int):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return "You're not set as leader, and don't have sufficient access level to override leadership."

        sql = "SELECT * FROM aodb a LEFT JOIN raid_loot r ON (a.name = r.name AND a.highql >= r.ql) " \
              "WHERE r.id = ? LIMIT 1"
        item = self.db.query_single(sql, [item_id])

        if item:
            self.add_item_to_loot(item.lowid, item.highid, item.ql, item.name, item.comment, item_count)

            return "Added %s to loot list." % item.name

        return "Failed to add item with ID %s." % item_id

    @command(command="loot", params=[Const("addraid"), Any("raid"), Any("category")],
             description="Add all loot from given raid", access_level="all")
    def loot_add_raid_loot(self, request, _, raid: str, category: str):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return "You're not set as leader, and don't have sufficient access level to override leadership."

        items = self.db.query(
            "SELECT r.raid, r.category, r.id, r.ql, r.name, r.comment, r.multiloot, a.lowid, a.highid, a.icon "
            "FROM raid_loot r "
            "LEFT JOIN aodb a "
            "ON (r.name = a.name AND r.ql <= a.highql) "
            "WHERE r.raid = ? AND r.category = ? "
            "ORDER BY r.name",
            [raid, category]
        )

        if items:
            for item in items:
                self.add_item_to_loot(item.lowid, item.highid, item.ql, item.name, item.comment, item.multiloot)

            return "%s table was added to loot." % category

        return "%s does not have any items registered in loot table." % category

    @command(command="raid", params=[Const("start"), Int("num_characters_max", is_optional=True), Any("raid_name")],
             description="Start new raid", access_level="moderator", sub_command="manage")
    def raid_start_cmd(self, request, _, raid_limit: int, raid_name: str):
        if self.raid:
            return "The raid, <yellow>%s<end>, is already running." % self.raid.raid_name

        raid_min_lvl = self.setting_service.get("default_min_lvl").get_value()

        self.raid = Raid(raid_name, request.sender.char_id, raid_min_lvl, raid_limit)

        leader_alts = self.alts_service.get_alts(request.sender.char_id)
        self.raid.raiders.append(Raider(leader_alts, request.sender.char_id))

        join_link = self.get_raid_join_blob("Click here")

        msg = "\n<yellow>----------------------------------------<end>\n"
        msg += "<yellow>%s<end> has just started the raid <yellow>%s<end>.\n" % (request.sender.name, raid_name)
        msg += "Raider limit: <highlight>%s<end>\n" % self.raid.raid_limit
        msg += "Min lvl: <highlight>%d<end>\n" % self.raid.raid_min_lvl
        msg += "%s to join\n" % join_link
        msg += "<yellow>----------------------------------------<end>"

        self.bot.send_org_message(msg)
        self.bot.send_private_channel_message(msg)

    @command(command="raid", params=[Options(["end", "cancel"])], description="End raid without saving/logging.",
             access_level="moderator", sub_command="manage")
    def raid_cancel_cmd(self, request, _):
        if self.raid is None:
            return "No raid is running."

        raid_name = self.raid.raid_name
        self.raid = None
        self.bot.send_org_message("%s canceled the raid <yellow>%s<end> prematurely."
                                  % (request.sender.name, raid_name))
        self.bot.send_private_channel_message("%s canceled the raid <yellow>%s<end> prematurely."
                                              % (request.sender.name, raid_name))

    @command(command="raid", params=[Const("join")], description="Join the ongoing raid", access_level="member")
    def raid_join_cmd(self, request, _):
        if self.raid:
            main_id = self.alts_service.get_main(request.sender.char_id).char_id
            in_raid = self.is_in_raid(main_id)

            player_level = self.db.query_single("SELECT level FROM player WHERE char_id = ?", [request.sender.char_id])
            player_level = player_level.level \
                if player_level is not None \
                else self.setting_service.get("default_min_lvl").get_value()

            if player_level < self.raid.raid_min_lvl:
                return "Your level (%d) does not meet the requirements of the raid (%d)." \
                       % (player_level, self.raid.raid_min_lvl)

            if in_raid is not None:
                if in_raid.active_id == request.sender.char_id:
                    if in_raid.is_active:
                        return "You're already participating in the raid."
                    else:
                        if not self.raid.is_open:
                            return "Raid is closed."
                        in_raid.is_active = True
                        in_raid.was_kicked = None
                        in_raid.was_kicked_reason = None
                        in_raid.left_raid = None
                        self.bot.send_private_channel_message("%s returned to actively participating in the raid."
                                                              % request.sender.name)
                        self.bot.send_org_message("%s returned to actively participating in the raid."
                                                  % request.sender.name)
                        return

                elif in_raid.is_active:
                    former_active_name = self.character_service.resolve_char_to_name(in_raid.active_id)
                    in_raid.active_id = request.sender.char_id
                    self.bot.send_private_channel_message("%s joined the raid with a different alt, <yellow>%s<end>."
                                                          % (former_active_name, request.sender.name))
                    self.bot.send_org_message("%s joined the raid with a different alt, <yellow>%s<end>."
                                              % (former_active_name, request.sender.name))
                    return

                elif not in_raid.is_active:
                    if not self.raid.is_open:
                        return "Raid is closed."
                    former_active_name = self.character_service.resolve_char_to_name(in_raid.active_id)
                    in_raid.active_id = request.sender.char_id
                    in_raid.was_kicked = None
                    in_raid.was_kicked_reason = None
                    in_raid.left_raid = None
                    self.bot.send_private_channel_message("%s returned to actively participate with "
                                                          "a different alt, <yellow>%s<end>."
                                                          % (former_active_name, request.sender.name))
                    self.bot.send_org_message("%s returned to actively participate with "
                                              "a different alt, <yellow>%s<end>."
                                              % (former_active_name, request.sender.name))
                    return
            elif self.raid.raid_limit is not None and len(self.raid.raiders) >= self.raid.raid_limit:
                return "Raid is full."
            elif self.raid.is_open:
                alts = self.alts_service.get_alts(request.sender.char_id)
                self.raid.raiders.append(Raider(alts, request.sender.char_id))
                self.bot.send_private_channel_message("<yellow>%s<end> joined the raid." % request.sender.name)
                self.bot.send_org_message("<yellow>%s<end> joined the raid." % request.sender.name)
                return

            return "Raid is closed."

        return "No raid is running."

    @command(command="raid", params=[Const("leave")], description="Leave the ongoing raid", access_level="member")
    def raid_leave_cmd(self, request, _):
        in_raid = self.is_in_raid(self.alts_service.get_main(request.sender.char_id).char_id)
        if in_raid:
            if not in_raid.is_active:
                return "You are not active in the raid."

            in_raid.is_active = False
            in_raid.left_raid = int(time.time())
            self.bot.send_private_channel_message("<yellow>%s<end> left the raid." % request.sender.name)
            self.bot.send_org_message("<yellow>%s<end> left the raid." % request.sender.name)
            return

        return "You are not in the raid."

    @command(command="raid", params=[Const("addpts"), Any("name")], description="Add points to all active participants",
             access_level="moderator", sub_command="manage")
    def points_add_cmd(self, request, _, name: str):
        preset = self.db.query_single("SELECT * FROM points_presets WHERE name = ?", [name])
        if preset:
            if self.raid:
                for raider in self.raid.raiders:
                    current_points = self.db.query_single("SELECT points, disabled FROM points WHERE char_id = ?",
                                                          [raider.main_id])

                    if raider.is_active:
                        if current_points and current_points.disabled == 0:
                            self.points_controller.alter_points(current_points.points, raider.main_id, preset.points,
                                                                request.sender.char_id, preset.name)
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
                return "<green>%d<end> points added to all active raiders." % preset.points
            else:
                return "No raid is running."

        return ChatBlob("No such preset - see list of presets", self.points_controller.build_preset_list())

    @command(command="raid", params=[Const("active")], description="Get a list of raiders to do active check",
             access_level="moderator", sub_command="manage")
    def raid_active_cmd(self, request, _):
        if self.raid:
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
                warn_link = self.text.make_chatcmd("Warn", "/tell <myname> raid cmd %s missed active "
                                                           "check, please give notice." % raider_name)
                blob += "<highlight>%s<end> [%s] [%s]\n" % (raider_name, akick_link, warn_link)
                raider_names.append(raider_name)
                count += 1

            if len(raider_names) > 0:
                active_check_names = "/assist "
                active_check_names += "\\n /assist ".join(raider_names)

                blob += "[<a href='chatcmd://%s'>Active check</a>]\n\n" % active_check_names
                raider_names.clear()

            return ChatBlob("Active check", blob)
        else:
            return "No raid is running."

    @command(command="raid", params=[Const("kick"), Character("char"), Any("reason")],
             description="Set raider as kicked with a reason", access_level="moderator", sub_command="manage")
    def raid_kick_cmd(self, _1, _2, char: SenderObj, reason: str):
        if self.raid is None:
            return "No raid is running."

        main_id = self.alts_service.get_main(char.char_id).char_id
        in_raid = self.is_in_raid(main_id)

        try:
            int(char.name)
            char.name = self.character_service.resolve_char_to_name(char.name)
        except ValueError:
            pass

        if in_raid is not None:
            if not in_raid.is_active:
                return "%s is already set as inactive." % char.name

            in_raid.is_active = False
            in_raid.was_kicked = int(time.time())
            in_raid.was_kicked_reason = reason
            return "%s has been kicked from the raid with reason \"%s\"" % (char.name, reason)

        return "%s is not participating." % char.name

    @command(command="raid", params=[Options(["open", "close"])], description="Open/close raid for new participants",
             access_level="moderator", sub_command="manage")
    def raid_open_close_cmd(self, request, action):
        if self.raid:
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

        return "No raid is running."

    @command(command="raid", params=[Const("save")], description="Save and log running raid", access_level="moderator", sub_command="manage")
    def raid_save_cmd(self, _1, _2):
        if self.raid:
            sql = "INSERT INTO raid_log (raid_name, started_by, raid_limit, raid_min_lvl, " \
                  "raid_start, raid_end) VALUES (?,?,?,?,?,?)"
            if self.db.exec(sql, [self.raid.raid_name, self.raid.started_by, self.raid.raid_limit,
                                  self.raid.raid_min_lvl, self.raid.started, int(time.time())]) > 0:
                raid_id = self.db.query_single("SELECT raid_id FROM raid_log ORDER BY raid_id DESC LIMIT 1").raid_id
                with_errors = len(self.raid.raiders)

                for raider in self.raid.raiders:
                    sql = "INSERT INTO raid_log_participants (raid_id, raider_id, accumulated_points, left_raid, " \
                          "was_kicked, was_kicked_reason) VALUES (?,?,?,?,?,?)"
                    with_errors -= self.db.exec(sql, [raid_id, raider.active_id, raider.accumulated_points,
                                                      raider.left_raid, raider.was_kicked, raider.was_kicked_reason])

                self.raid = None

                return "Raid saved%s." % ("" if with_errors == 0 else " with %d errors when "
                                                                      "logging participants" % with_errors)
            else:
                return "Failed to log raid. Try again or cancel raid to end raid."

        return "No raid is running."

    @command(command="raid", params=[Const("logentry"), Int("raid_id"), Character("char", is_optional=True)],
             description="Show log entry for raid, with possibility of narrowing down the log for character in raid",
             access_level="moderator", sub_command="manage")
    def raid_log_entry_cmd(self, _1, _2, raid_id: int, char: SenderObj):
        log_entry_spec = None
        if char:
            sql = "SELECT * FROM raid_log r LEFT JOIN raid_log_participants p ON r.raid_id = p.raid_id " \
                  "WHERE r.raid_id = ? AND p.raider_id = ?"
            log_entry_spec = self.db.query_single(sql, [raid_id, char.char_id])

        sql = "SELECT * FROM raid_log r LEFT JOIN raid_log_participants p ON r.raid_id = p.raid_id " \
              "WHERE r.raid_id = ? ORDER BY p.accumulated_points DESC"
        log_entry = self.db.query(sql, [raid_id])
        pts_sum = self.db.query_single("SELECT SUM(p.accumulated_points) AS sum FROM raid_log_participants p "
                                       "WHERE p.raid_id = ?", [raid_id]).sum

        if log_entry:
            blob = "Raid name: <highlight>%s<end>\n" % log_entry[0].raid_name
            blob += "Raid limit: <highlight>%s<end>\n" % log_entry[0].raid_limit
            blob += "Raid min lvl: <highlight>%s<end>\n" % log_entry[0].raid_min_lvl
            blob += "Started by: <highlight>%s<end>\n" \
                    % self.character_service.resolve_char_to_name(log_entry[0].started_by)
            blob += "Start time: <highlight>%s<end>\n" % self.util.format_datetime(log_entry[0].raid_start)
            blob += "End time: <highlight>%s<end>\n" % self.util.format_datetime(log_entry[0].raid_end)
            blob += "Run time: <highlight>%s<end>\n" \
                    % self.util.time_to_readable(log_entry[0].raid_end - log_entry[0].raid_start)
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
                blob += "%s - %d points earned [%s] [%s] [%s]\n" % (raider_name, raider.accumulated_points,
                                                                    log_link, account_link, alt_link)

            log_entry_reference = "the raid %s" % log_entry[0].raid_name \
                if char is None \
                else "%s in raid %s" \
                     % (self.character_service.resolve_char_to_name(char.char_id), log_entry[0].raid_name)
            return ChatBlob("Log entry for %s" % log_entry_reference, blob)

        return "No such log entry."

    @command(command="raid", params=[Const("history")], description="Show a list of recent raids",
             access_level="member")
    def raid_history_cmd(self, _1, _2):
        sql = "SELECT * FROM raid_log ORDER BY raid_end DESC LIMIT 30"
        raids = self.db.query(sql)

        if raids:
            blob = ""
            for raid in raids:
                participant_link = self.text.make_chatcmd("Log", "/tell <myname> raid logentry %d" % raid.raid_id)
                timestamp = self.util.format_datetime(raid.raid_start)
                leader_name = self.character_service.resolve_char_to_name(raid.started_by)
                blob += "[%d] [%s] <orange>%s<end> started by <yellow>%s<end> [%s]\n" \
                        % (raid.raid_id, timestamp, raid.raid_name, leader_name, participant_link)

            return ChatBlob("Raid history", blob)

    @timerevent(budatime="1h", description="Periodically check when loot list was last modified, "
                                           "and clear it if last modification was done 1+ hours ago")
    def loot_clear_event(self, _1, _2):
        if self.loot_list and self.last_modify:
            if int(time.time()) - self.last_modify > 3600 and self.loot_list:
                self.last_modify = None
                self.loot_list = OrderedDict()
                self.bot.send_org_message("Loot was last modified more than 1 hour ago, list has been cleared.")
                self.bot.send_private_channel_message("Loot was last modified more than "
                                                      "1 hour ago, list has been cleared.")

    def is_already_added(self, name: str):
        for i, loot_item in self.loot_list.items():
            if name in loot_item.bidders:
                return loot_item
        return None

    def add_item_to_loot(self, low_id: int, high_id: int, ql: int, name: str, comment=None, item_count=1):
        end_index = list(self.loot_list.keys())[-1] + 1 if len(self.loot_list) > 0 else 1

        item_name = "%s (%s)" % (name, comment) if comment is not None and comment != "" else name

        item_ref = {
            "low_id": low_id,
            "high_id": high_id,
            "ql": ql,
            "name": item_name
        }

        self.loot_list[end_index] = LootItem(item_ref, None, None, item_count)
        self.last_modify = int(time.time())

    def is_in_raid(self, main_id: int):
        if self.raid is None:
            return None

        for raider in self.raid.raiders:
            if raider.main_id == main_id:
                return raider

    def get_loot_list(self):
        blob = ""

        for i, loot_item in self.loot_list.items():
            item = loot_item.item
            bidders = loot_item.bidders

            increase_link = self.text.make_chatcmd("+", "/tell <myname> loot increase %d" % i)
            decrease_link = self.text.make_chatcmd("-", "/tell <myname> loot decrease %d" % i)

            blob += "%d. %s " % (i, self.text.make_item(item.low_id, item.high_id, item.ql, item.name))
            blob += "x%s [%s|%s]\n" % (loot_item.count, increase_link, decrease_link)

            if len(bidders) > 0:
                blob += " | %s\n" % ', '.join(bidders)
            else:
                blob += " | No bidders\n"

            add_to_loot = self.text.make_chatcmd("Add to", "/tell <myname> loot add %d" % i)
            remove_from_loot = self.text.make_chatcmd("Remove from", "/tell <myname> loot rem")
            remove_item = self.text.make_chatcmd("Remove item", "/tell <myname> loot remitem %d" % i)
            blob += " | [%s] [%s] [%s]\n\n" % (add_to_loot, remove_from_loot, remove_item)

        return ChatBlob("Loot (%d)" % len(self.loot_list), blob)

    def get_auction_list(self):
        blob = ""
        item = None

        for i, loot_item in self.loot_list.items():
            item = loot_item.item
            bidders = loot_item.bidders

            item_ref = self.text.make_item(item.low_id, item.high_id, item.ql, item.name)
            prefix = "" if loot_item.prefix is None else "%s " % loot_item.prefix
            suffix = "" if loot_item.suffix is None else " %s" % loot_item.suffix
            blob += "%d. %s%s%s\n" % (i, prefix, item_ref, suffix)

            if len(bidders) > 0:
                blob += " | <red>%s<end> bidder%s\n" % (len(bidders), "s" if len(bidders) > 1 else "")
            else:
                blob += " | <green>No bidders<end>\n"

            if len(self.loot_list) > 1:
                bid_link = self.text.make_chatcmd("Bid", "/tell <myname> bid item %d" % i)
                blob += " | [%s]\n\n" % bid_link

        if len(self.loot_list) == 1:
            min_bid = self.setting_service.get("minimum_bid").get_value()
            blob += "\n"
            blob += "<header2>Bid info<end>\n" \
                    "To bid for <yellow>%s<end>, you must send a tell to <myname> with\n\n" \
                    "<tab><highlight>/tell <myname> auction bid &lt;amount&gt;<end>\n\n" \
                    "Where you replace &lt;amount&gt; with the amount of points you're welling to bid " \
                    "for the item.\n\nMinimum bid is %d, and you can also use \"all\" as bid, to bid " \
                    "all your available points.\n\n" % (item.name, min_bid)
            if self.setting_service.get("vickrey_auction").get_value():
                blob += "<header2>This is a Vickrey auction<end>\n" \
                        " - In a Vickrey auction, you only get to bid twice on the same item.\n" \
                        " - You won't be notified of the outcome of your bid, as all bids will be anonymous.\n" \
                        " - The highest anonymous bid will win, and pay the second-highest bid.\n" \
                        " - Bids are anonymous, meaning you do not share your bid with others, or write this command " \
                        "in the raid channel.\n - Bidding is done with the command described above. You'll be " \
                        "notified when/if the bid has been accepted."

        return ChatBlob("Auction list (%d)" % len(self.loot_list), blob)

    def get_raid_join_blob(self, link_txt: str):
        blob = "<header2>1. Join the raid<end>\n" \
               "To join the current raid <yellow>%s<end>, send the following tell to <myname>\n" \
               "<tab><tab><a href='chatcmd:///tell <myname> <symbol>raid join'>/tell <myname> raid " \
               "join</a>\nOr write <a href='chatcmd:///group <myname> <symbol>raid join'><symbol>raid " \
               "join</a> in the raid channel.\n\n<header2>2. Enable LFT<end>\nWhen you have joined the raid, go lft " \
               "with \"<myname>\" as description\n<tab><tab><a href='chatcmd:///lft <myname>'>/lft <myname></a>\n\n" \
               "<header2>3. Announce<end>\nYou could announce to the raid leader, that you have enabled " \
               "LFT\n<tab><tab><a href='chatcmd:///group <myname> I am on lft'>Announce</a> that you have enabled " \
               "lft\n\n<header2>4. Rally with yer mateys<end>\nFinally, move towards the starting location of " \
               "the raid.\n<highlight>Ask for help<end> if you're in doubt of where to go." % self.raid.raid_name

        return self.text.paginate(link_txt, blob, 5000, 1)[0]
