from core.access_service import AccessService
from core.chat_blob import ChatBlob
from core.command_param_types import Const, Int, Item, Any
from core.db import DB
from core.decorators import instance, command, timerevent
from core.text import Text
from core.tyrbot import Tyrbot
from .leader_controller import LeaderController
from collections import OrderedDict
import secrets
import time


class AOItem:
    def __init__(self, low_id, high_id, ql, name, icon_id=None):
        self.low_id = low_id
        self.high_id = high_id
        self.ql = ql
        self.name = name
        self.icon_id = icon_id


class LootItem:
    def __init__(self, item, count=1):
        item = AOItem(item["low_id"], item["high_id"], item["ql"], item["name"])
        self.item: AOItem = item
        self. bidders = []
        self.count = count


@instance()
class RaidController:
    def __init__(self):
        self.loot_list = OrderedDict()
        self.last_modify = None

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.leader_controller: LeaderController = registry.get_instance("leader_controller")
        self.access_service: AccessService = registry.get_instance("access_service")

    @command(command="loot", params=[], description="Show the list of added items", access_level="all")
    def loot_cmd(self, request):
        if not self.loot_list:
            return "Loot list is empty."

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

    @command(command="loot", params=[Const("remitem"), Int("item_index")], description="Remove existing loot", access_level="all")
    def loot_rem_item_cmd(self, request, _, item_index):
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

    @command(command="loot", params=[Const("additem"), Item("item"), Int("item_count", is_optional=True)], description="Add an item to loot list", access_level="all")
    def loot_add_item_cmd(self, request, _, item, item_count):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return "You're not set as leader, and don't have sufficient access level to override leadership."

        if item_count is None:
            item_count = 1

        self.add_item_to_loot(item["low_id"], item["high_id"], item["ql"], item["name"], None, item_count)

        return "%s was added to loot list." % item["name"]

    @command(command="loot", params=[Const("increase"), Int("item_index")], description="Increase item count", access_level="all")
    def loot_increase_item_cmd(self, request, _, item_index):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return "You're not set as leader, and don't have sufficient access level to override leadership."

        if not self.loot_list:
            return "Loot list is empty."

        try:
            loot_item = self.loot_list[item_index]

            if loot_item:
                loot_item.count = loot_item.count + 1
                self.last_modify = int(time.time())
                return "Increased item count for %s to %d." % (loot_item.item.name, loot_item.count)
            else:
                return "Item error."
        except KeyError:
            return "Wrong index given."

    @command(command="loot", params=[Const("decrease"), Int("item_index")], description="Decrease item count", access_level="all")
    def loot_decrease_item_cmd(self, request, _, item_index):
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

    @command(command="loot", params=[Const("add"), Int("item_index")], description="Add yourself to item", access_level="all")
    def loot_add_to_cmd(self, request, _, item_index):
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

                return "%s moved from %s to %s." % (name, old_item.item.name, loot_item.item.name) if old_item is not None else "%s added to %s." % (name, loot_item.item.name)
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
                    blob += "%s. %s (ql%s)\n" % (i, self.text.make_item(item.low_id, item.high_id, item.ql, item.name), item.ql)
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

    @command(command="loot", params=[Const("additem"), Const("raid"), Int("item_id"), Int("item_count")], description="Used by the loot lists to add items to loot list", access_level="all")
    def loot_add_raid_item(self, request, _1, _2, item_id, item_count):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return "You're not set as leader, and don't have sufficient access level to override leadership."

        sql = "SELECT * FROM aodb a LEFT JOIN raid_loot r ON (a.name = r.name AND a.highql >= r.ql) WHERE r.id = ? LIMIT 1"
        item = self.db.query_single(sql, [item_id])

        if item:
            self.add_item_to_loot(item.lowid, item.highid, item.ql, item.name, item.comment, item_count)

            return "Added %s to loot list." % item.name

        return "Failed to add item with ID %s." % item_id

    @command(command="loot", params=[Const("addraid"), Const("APF"), Any("category")], description="Add all loot from given raid", access_level="all")
    def loot_add_raid_loot(self, request, _1, _2, category):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return "You're not set as leader, and don't have sufficient access level to override leadership."

        items = self.db.query(
            "SELECT r.raid, r.category, r.id, r.ql, r.name, r.comment, r.multiloot, a.lowid, a.highid, a.icon "
            "FROM raid_loot r "
            "LEFT JOIN aodb a "
            "ON (r.name = a.name AND r.ql <= a.highql) "
            "WHERE r.raid = 'APF' AND r.category = ? "
            "ORDER BY r.name",
            [category]
        )

        if items:
            for item in items:
                self.add_item_to_loot(item.lowid, item.highid, item.ql, item.name, item.comment, item.multiloot)

            return "%s table was added to loot." % category

        return "%s does not have any items registered in loot table." % category

    @timerevent(budatime="1h", description="Periodically check when loot list was last modified, and clear it if last modification was done 1+ hours ago")
    def loot_clear_event(self, event_type, event_data):
        if self.loot_list and self.last_modify:
            if int(time.time()) - self.last_modify > 3600 and self.loot_list:
                self.last_modify = None
                self.loot_list = OrderedDict()
                self.bot.send_org_message("Loot was last modified more than 1 hour ago, list has been cleared.")
                self.bot.send_private_channel_message("Loot was last modified more than 1 hour ago, list has been cleared.")

    def is_already_added(self, name):
        for i, loot_item in self.loot_list.items():
            if name in loot_item.bidders:
                return loot_item
        return None

    def add_item_to_loot(self, low_id, high_id, ql, name, comment=None, item_count=1):
        end_index = list(self.loot_list.keys())[-1] + 1 if len(self.loot_list) > 0 else 1

        item_name = "%s (%s)" % (name, comment) if comment is not None and comment != "" else name

        item_ref = {
            "low_id": low_id,
            "high_id": high_id,
            "ql": ql,
            "name": item_name
        }

        self.loot_list[end_index] = LootItem(item_ref, item_count)
        self.last_modify = int(time.time())
