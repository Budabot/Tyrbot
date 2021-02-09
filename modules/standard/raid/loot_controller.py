import re
import secrets
import time
from collections import OrderedDict

from core.chat_blob import ChatBlob
from core.command_param_types import Const, Int, Any
from core.db import DB
from core.decorators import instance, command, timerevent
from core.setting_service import SettingService
from core.text import Text
from modules.standard.items.items_controller import ItemsController
from .item_types import LootItem
from .leader_controller import LeaderController


@instance()
class LootController:
    def __init__(self):
        self.loot_list = OrderedDict()
        self.last_modify = None

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.leader_controller: LeaderController = registry.get_instance("leader_controller")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.items_controller: ItemsController = registry.get_instance("items_controller")
        self.raid_controller = registry.get_instance("raid_controller")

    @command(command="loot", params=[], description="Show the list of added items", access_level="all")
    def loot_cmd(self, request):
        if not self.loot_list:
            return "Loot list is empty."

        return self.get_loot_list()

    @command(command="loot", params=[Const("clear")], description="Clear all loot", access_level="all", sub_command="modify")
    def loot_clear_cmd(self, request, _):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

        if self.loot_list:
            self.loot_list.clear()
            self.last_modify = None
            self.raid_controller.send_message("Loot list cleared.")
        else:
            return "Loot list is already empty."

    @command(command="loot", params=[Const("remitem"), Int("item_index")],
             description="Remove an existing loot item", access_level="all", sub_command="modify")
    def loot_rem_item_cmd(self, request, _, item_index: int):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

        if not self.loot_list:
            return "Loot list is empty."

        if item_index not in self.loot_list:
            return "No item at index <highlight>%d</highlight> exists." % item_index

        item = self.loot_list.pop(item_index)
        self.last_modify = int(time.time())
        self.raid_controller.send_message("Removed %s from loot list." % item.get_item_str())

    @command(command="loot", params=[Const("increase"), Int("item_index")], description="Increase item count",
             access_level="all", sub_command="modify")
    def loot_increase_item_cmd(self, request, _, item_index: int):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

        if not self.loot_list:
            return "Loot list is empty."

        if item_index not in self.loot_list:
            return "No item at index <highlight>%d</highlight> exists." % item_index

        loot_item = self.loot_list[item_index]
        loot_item.count += 1
        self.last_modify = int(time.time())
        return "Increased item count for %s to %d." % (loot_item.get_item_str(), loot_item.count)

    @command(command="loot", params=[Const("decrease"), Int("item_index")], description="Decrease item count",
             access_level="all", sub_command="modify")
    def loot_decrease_item_cmd(self, request, _, item_index: int):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

        if not self.loot_list:
            return "Loot list is empty."

        if item_index not in self.loot_list:
            return "No item at index <highlight>%d</highlight> exists." % item_index

        loot_item = self.loot_list[item_index]
        loot_item.count = loot_item.count - 1 if loot_item.count > 1 else 1
        self.last_modify = int(time.time())
        return "Decreased item count for %s to %d." % (loot_item.get_item_str(), loot_item.count)

    @command(command="loot", params=[Const("add"), Int("item_index")], description="Add yourself to item roll",
             access_level="all")
    def loot_add_to_cmd(self, request, _, item_index: int):
        if item_index not in self.loot_list:
            return "No item at index <highlight>%d</highlight> exists." % item_index

        loot_item = self.loot_list[item_index]
        old_item = self.is_already_added(request.sender.name)

        if old_item:
            if old_item.get_item_str() == loot_item.get_item_str():
                return "You have already added to %s." % loot_item.get_item_str()

            old_item.bidders.remove(request.sender.name)

        loot_item.bidders.append(request.sender.name)

        self.last_modify = int(time.time())

        if old_item is not None:
            return "You have moved from %s to %s." % (old_item.get_item_str(), loot_item.get_item_str())
        else:
            return "You have added to %s." % loot_item.get_item_str()

    @command(command="loot", params=[Const("rem")], description="Remove yourself from item roll", access_level="all")
    def loot_rem_from_cmd(self, request, _):
        loot_item = self.is_already_added(request.sender.name)

        if loot_item is not None:
            loot_item.bidders.remove(request.sender.name)

            self.last_modify = int(time.time())

            return "You were removed from %s." % loot_item.get_item_str()
        else:
            return "You are not added to any loot."

    @command(command="loot", params=[Const("roll")], description="Roll all loot", access_level="all", sub_command="modify")
    def loot_roll_cmd(self, request, _):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

        if not self.loot_list:
            return "Loot list is empty."

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

                blob += "%d. %s\n" % (i, loot_item.get_item_str())
                blob += " | Winners: <red>%s</red>\n\n" % '</red>, <red>'.join(winners)

        if len(blob) > 0:
            self.raid_controller.send_message(ChatBlob("Roll results", blob))
        else:
            return "No one was added to any loot."

    @command(command="loot", params=[Const("reroll")], description="Rebuild loot list", access_level="all", sub_command="modify")
    def loot_reroll_cmd(self, request, _):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

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

            self.raid_controller.send_message("Loot that was not won is being re-rolled.")
            self.raid_controller.send_message(self.get_loot_list())
        else:
            return "Loot list is empty."

    @command(command="loot", params=[Const("addraiditem"), Int("raid_item_id"), Int("item_count")],
             description="Add item from pre-defined raid to loot list", access_level="all", sub_command="modify")
    def loot_add_raid_item(self, request, _, raid_item_id: int, item_count: int):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

        sql = "SELECT r.name, r.comment,  r.ql, a.lowid AS low_id, a.highid AS high_id FROM aodb a LEFT JOIN raid_loot r ON (a.name = r.name AND a.highql >= r.ql) " \
              "WHERE r.id = ? LIMIT 1"
        item = self.db.query_single(sql, [raid_item_id])

        if item:
            self.add_item_to_loot(item, item.comment, item_count)
            self.raid_controller.send_message("Added <highlight>%s</highlight> to loot list." % item.name)
        else:
            return "Could not find raid item with ID <highlight>%s</highlight>." % raid_item_id

    @command(command="loot", params=[Const("addraid"), Any("raid"), Any("category")],
             description="Add all loot from pre-defined raid", access_level="all", sub_command="modify")
    def loot_add_raid_loot(self, request, _, raid: str, category: str):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

        items = self.db.query(
            "SELECT r.raid, r.category, r.id, r.ql, r.name, r.comment, r.multiloot, a.lowid AS low_id, a.highid AS high_id, a.icon "
            "FROM raid_loot r "
            "LEFT JOIN aodb a "
            "ON (r.name = a.name AND r.ql <= a.highql) "
            "WHERE r.raid = ? AND r.category = ? "
            "ORDER BY r.name",
            [raid, category]
        )

        if items:
            for item in items:
                self.add_item_to_loot(item, item.comment, item.multiloot)

            self.raid_controller.send_message("<highlight>%s</highlight> loot table was added to loot list." % category)
        else:
            return "<highlight>%s</highlight> does not have any items registered in loot table." % category

    @command(command="loot", params=[Const("additem", is_optional=True), Int("item"), Int("item_count", is_optional=True)],
             description="Add an item to loot list by item id", access_level="all", sub_command="modify")
    def loot_add_item_id_cmd(self, request, _, item_id, item_count: int):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

        if item_count is None:
            item_count = 1

        item = self.items_controller.get_by_item_id(item_id)
        if not item:
            return "Could not find item with ID <highlight>%d</highlight>." % item_id

        self.add_item_to_loot(item, None, item_count)
        self.raid_controller.send_message("%s was added to loot list." % item.name)

    @command(command="loot", params=[Const("additem", is_optional=True), Any("item"), Int("item_count", is_optional=True)],
             description="Add an item to loot list", access_level="all", sub_command="modify")
    def loot_add_item_cmd(self, request, _, item, item_count: int):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

        loot = ""
        if item_count is None:
            item_count = 1
        items = re.findall(r"(([^<]+)?<a href=[\"\']itemref://(\d+)/(\d+)/(\d+)[\"\']>([^<]+)</a>([^<]+)?)", item)
        if items and item_count == 1:
            for item in items:
                item = self.text.make_item(int(item[2]), int(item[3]), int(item[4]), item[5])
                if loot != "":
                    loot += ", " + item
                else:
                    loot += item
                self.add_item_to_loot(item)
        else:
            loot += item
            self.add_item_to_loot(item, None, item_count)

        self.raid_controller.send_message("%s was added to loot list." % loot)

    @timerevent(budatime="1h", description="Periodically check when loot list was last modified, and clear it if last modification was done 1+ hours ago")
    def loot_clear_event(self, _1, _2):
        if self.loot_list and self.last_modify:
            if int(time.time()) - self.last_modify > 3600 and self.loot_list:
                self.last_modify = None
                self.loot_list = OrderedDict()

                self.raid_controller.send_message("Loot was last modified more than 1 hour ago, list has been cleared.")

    def is_already_added(self, name: str):
        for i, loot_item in self.loot_list.items():
            if name in loot_item.bidders:
                return loot_item
        return None

    def add_item_to_loot(self, item, comment=None, item_count=1):
        existing_item = next((loot_item for x, loot_item in self.loot_list.items() if loot_item.item == item), None)
        if existing_item:
            existing_item.count += 1
        else:
            # this prevents loot items from being re-numbered when items are removed
            end_index = list(self.loot_list.keys())[-1] + 1 if len(self.loot_list) > 0 else 1

            self.loot_list[end_index] = LootItem(item, comment, item_count)

        self.last_modify = int(time.time())

    def get_loot_list(self):
        blob = ""

        for i, loot_item in self.loot_list.items():
            bidders = loot_item.bidders

            blob += "%d. %s x%d" % (i, loot_item.get_item_str(), loot_item.count)

            add_to_loot = self.text.make_tellcmd("Join", "loot add %d" % i)
            remove_from_loot = self.text.make_tellcmd("Leave", "loot rem")
            blob += " [%s] [%s]\n" % (add_to_loot, remove_from_loot)

            if len(bidders) > 0:
                blob += " | %s\n" % ', '.join(bidders)
            else:
                blob += " | No bidders\n"
            blob += "\n"

        return ChatBlob("Loot (%d)" % len(self.loot_list), blob)
