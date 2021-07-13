import re
import secrets
import time
from collections import OrderedDict

from core.chat_blob import ChatBlob
from core.command_param_types import Const, Int, Any, Options
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
        self.clear_loot_list()
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
        if not self.get_loot_list():
            return "Loot list is empty."

        return self.get_loot_list_display()

    @command(command="loot", params=[Const("clear")], description="Clear all loot", access_level="all", sub_command="modify")
    def loot_clear_cmd(self, request, _):
        if not self.leader_controller.can_use_command(request.sender.char_id, request.conn):
            return LeaderController.NOT_LEADER_MSG

        if self.get_loot_list():
            self.get_loot_list().clear()
            self.last_modify = None
            self.raid_controller.send_message("Loot list has been cleared.", request.conn)
        else:
            return "Loot list is already empty."

    @command(command="loot", params=[Options(["rem", "remove"]), Int("item_index")],
             description="Remove an existing loot item", access_level="all", sub_command="modify")
    def loot_rem_item_cmd(self, request, _, item_index: int):
        if not self.leader_controller.can_use_command(request.sender.char_id, request.conn):
            return LeaderController.NOT_LEADER_MSG

        if not self.get_loot_list():
            return "Loot list is empty."

        if item_index not in self.get_loot_list():
            return "No item at index <highlight>%d</highlight> exists." % item_index

        item = self.get_loot_list().pop(item_index)
        self.last_modify = int(time.time())
        self.raid_controller.send_message("Removed %s from loot list." % item.get_item_str(), request.conn)

    @command(command="loot", params=[Const("increase"), Int("item_index")], description="Increase item count",
             access_level="all", sub_command="modify")
    def loot_increase_item_cmd(self, request, _, item_index: int):
        if not self.leader_controller.can_use_command(request.sender.char_id, request.conn):
            return LeaderController.NOT_LEADER_MSG

        if not self.get_loot_list():
            return "Loot list is empty."

        if item_index not in self.get_loot_list():
            return "No item at index <highlight>%d</highlight> exists." % item_index

        loot_item = self.get_loot_list()[item_index]
        loot_item.count += 1
        self.last_modify = int(time.time())
        return "Increased item count for %s to %d." % (loot_item.get_item_str(), loot_item.count)

    @command(command="loot", params=[Const("decrease"), Int("item_index")], description="Decrease item count",
             access_level="all", sub_command="modify")
    def loot_decrease_item_cmd(self, request, _, item_index: int):
        if not self.leader_controller.can_use_command(request.sender.char_id, request.conn):
            return LeaderController.NOT_LEADER_MSG

        if not self.get_loot_list():
            return "Loot list is empty."

        if item_index not in self.get_loot_list():
            return "No item at index <highlight>%d</highlight> exists." % item_index

        loot_item = self.get_loot_list()[item_index]
        loot_item.count = loot_item.count - 1 if loot_item.count > 1 else 1
        self.last_modify = int(time.time())
        return "Decreased item count for %s to %d." % (loot_item.get_item_str(), loot_item.count)

    @command(command="loot", params=[Const("join"), Int("item_index")], description="Add yourself to item roll",
             access_level="all")
    def loot_add_to_cmd(self, request, _, item_index: int):
        if item_index not in self.get_loot_list():
            return "No item at index <highlight>%d</highlight> exists." % item_index

        loot_item = self.get_loot_list()[item_index]
        old_item = self.is_already_added(request.sender.name)

        if old_item:
            if old_item.get_item_str() == loot_item.get_item_str():
                return "You have already joined the loot roll for %s." % loot_item.get_item_str()

            old_item.bidders.remove(request.sender.name)

        loot_item.bidders.append(request.sender.name)

        self.last_modify = int(time.time())

        if old_item is not None:
            return "You have left the loot roll for %s and joined the loot roll for %s." % (old_item.get_item_str(), loot_item.get_item_str())
        else:
            return "You have joined the loot roll for %s." % loot_item.get_item_str()

    @command(command="loot", params=[Const("leave")], description="Remove yourself from item roll", access_level="all")
    def loot_rem_from_cmd(self, request, _):
        loot_item = self.is_already_added(request.sender.name)

        if loot_item is not None:
            loot_item.bidders.remove(request.sender.name)

            self.last_modify = int(time.time())

            return "You left the loot roll for %s." % loot_item.get_item_str()
        else:
            return "You have not joined any loot roll."

    @command(command="loot", params=[Const("roll")], description="Roll all loot", access_level="all", sub_command="modify")
    def loot_roll_cmd(self, request, _):
        if not self.leader_controller.can_use_command(request.sender.char_id, request.conn):
            return LeaderController.NOT_LEADER_MSG

        if not self.get_loot_list():
            return "Loot list is empty."

        blob = ""
        for i, loot_item in self.get_loot_list().copy().items():
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
                        loot_item.count = loot_item.count - 1

                blob += "%d. %s\n" % (i, loot_item.get_item_str())
                blob += "  Winners: <red>%s</red>\n\n" % '</red>, <red>'.join(winners)

            if loot_item.count == 0:
                self.get_loot_list().pop(i)

        if len(blob) > 0:
            self.raid_controller.send_message(ChatBlob("Roll results", blob), request.conn)
        else:
            return "No one was added to any loot."

    @command(command="loot", params=[Const("reroll")], description="Rebuild loot list", access_level="all", sub_command="modify")
    def loot_reroll_cmd(self, request, _):
        if not self.leader_controller.can_use_command(request.sender.char_id, request.conn):
            return LeaderController.NOT_LEADER_MSG

        if self.get_loot_list():
            count = 1
            for key in sorted(list(self.get_loot_list().keys())):
                if self.get_loot_list()[key].count <= 0:
                    del self.get_loot_list()[key]
                else:
                    loot_item = self.get_loot_list()[key]
                    del self.get_loot_list()[key]
                    self.get_loot_list()[count] = loot_item
                    count += 1

            self.last_modify = int(time.time())

            self.raid_controller.send_message("Loot that was not won is being re-rolled.", request.conn)
            self.raid_controller.send_message(self.get_loot_list_display(), request.conn)
        else:
            return "Loot list is empty."

    @command(command="loot", params=[Const("addraiditem"), Int("raid_item_id"), Int("item_count")],
             description="Add item from pre-defined raid to loot list", access_level="all", sub_command="modify")
    def loot_add_raid_item(self, request, _, raid_item_id: int, item_count: int):
        if not self.leader_controller.can_use_command(request.sender.char_id, request.conn):
            return LeaderController.NOT_LEADER_MSG

        sql = "SELECT r.name, r.comment, r.ql, a.lowid AS low_id, a.highid AS high_id, a.icon FROM aodb a LEFT JOIN raid_loot r ON (a.name = r.name AND a.highql >= r.ql) " \
              "WHERE r.id = ? LIMIT 1"
        item = self.db.query_single(sql, [raid_item_id])

        if item:
            self.add_item_to_loot(item, item.comment, item_count)
            self.raid_controller.send_message("Added <highlight>%s</highlight> to loot list." % item.name, request.conn)
        else:
            return "Could not find raid item with ID <highlight>%s</highlight>." % raid_item_id

    @command(command="loot", params=[Const("addraid"), Any("raid"), Any("category")],
             description="Add all loot from pre-defined raid", access_level="all", sub_command="modify")
    def loot_add_raid_loot(self, request, _, raid: str, category: str):
        if not self.leader_controller.can_use_command(request.sender.char_id, request.conn):
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

            self.raid_controller.send_message("<highlight>%s</highlight> loot table was added to loot list." % category, request.conn)
        else:
            return "<highlight>%s</highlight> does not have any items registered in loot table." % category

    @command(command="loot", params=[Const("add", is_optional=True), Int("item"), Int("item_count", is_optional=True)],
             description="Add an item to loot list by item id", access_level="all", sub_command="modify")
    def loot_add_item_id_cmd(self, request, _, item_id, item_count: int):
        if not self.leader_controller.can_use_command(request.sender.char_id, request.conn):
            return LeaderController.NOT_LEADER_MSG

        if item_count is None:
            item_count = 1

        item = self.items_controller.get_by_item_id(item_id)
        if not item:
            return "Could not find item with ID <highlight>%d</highlight>." % item_id

        item.low_id = item.lowid
        item.high_id = item.highid
        item.ql = item.highql

        self.add_item_to_loot(item, None, item_count)
        self.raid_controller.send_message("%s was added to loot list." % item.name, request.conn)

    @command(command="loot", params=[Const("add", is_optional=True), Any("item"), Int("item_count", is_optional=True)],
             description="Add an item to loot list", access_level="all", sub_command="modify")
    def loot_add_item_cmd(self, request, _, item, item_count: int):
        if not self.leader_controller.can_use_command(request.sender.char_id, request.conn):
            return LeaderController.NOT_LEADER_MSG

        loot = ""
        if item_count is None:
            item_count = 1
        items = re.findall(r"(([^<]+)?<a href=[\"\']itemref://(\d+)/(\d+)/(\d+)[\"\']>([^<]+)</a>([^<]+)?)", item)
        if items:
            for _1, _2, low_id, high_id, ql, name, _3 in items:
                item_link = self.text.make_item(int(low_id), int(high_id), int(ql), name)
                if loot != "":
                    loot += ", " + item_link
                else:
                    loot += item_link

                row = self.items_controller.get_by_item_id(high_id, ql)
                if row:
                    row.low_id = row.lowid
                    row.high_id = row.highid
                    row.ql = row.highql
                    self.add_item_to_loot(row, None, item_count)
                else:
                    self.add_item_to_loot(item_link, None, item_count)
        else:
            loot = item
            self.add_item_to_loot(item, None, item_count)

        self.raid_controller.send_message("%s was added to loot list." % loot, request.conn)

    @timerevent(budatime="1h", description="Periodically check when loot list was last modified, and clear it if last modification was done 1+ hours ago")
    def loot_clear_event(self, _1, _2):
        if self.get_loot_list() and self.last_modify:
            if int(time.time()) - self.last_modify > 3600 and self.get_loot_list():
                self.last_modify = None
                self.clear_loot_list()

                # TODO get conn
                self.raid_controller.send_message("Loot was last modified more than 1 hour ago, list has been cleared.", self.bot.get_temp_conn())

    def is_already_added(self, name: str):
        for i, loot_item in self.get_loot_list().items():
            if name in loot_item.bidders:
                return loot_item
        return None

    def add_item_to_loot(self, item, comment=None, item_count=1):
        existing_item = next((loot_item for x, loot_item in self.get_loot_list().items() if loot_item.item == item), None)
        if existing_item:
            existing_item.count += 1
        else:
            # this prevents loot items from being re-numbered when items are removed
            end_index = list(self.get_loot_list().keys())[-1] + 1 if len(self.get_loot_list()) > 0 else 1

            self.get_loot_list()[end_index] = LootItem(item, comment, item_count)

        self.last_modify = int(time.time())

    def get_loot_list_display(self):
        blob = ""

        for i, loot_item in self.get_loot_list().items():
            bidders = loot_item.bidders

            item_image = loot_item.get_item_image()
            if item_image:
                blob += item_image + "\n"

            blob += "%d. %s x%d" % (i, loot_item.get_item_str(), loot_item.count)

            add_to_loot = self.text.make_tellcmd("Join", "loot join %d" % i)
            remove_from_loot = self.text.make_tellcmd("Leave", "loot leave")
            blob += " [%s] [%s]\n" % (add_to_loot, remove_from_loot)

            if len(bidders) > 0:
                blob += "Bidders: %s\n" % ', '.join(bidders)
            else:
                blob += "Bidders: -\n"
            blob += "\n\n"

        return ChatBlob("Loot (%d)" % len(self.get_loot_list()), blob)

    def clear_loot_list(self):
        self.loot_list = OrderedDict()

    def get_loot_list(self):
        return self.loot_list
