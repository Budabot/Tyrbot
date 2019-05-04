import secrets
import time
from collections import OrderedDict

from core.chat_blob import ChatBlob
from core.command_param_types import Const, Int, Item, Any
from core.db import DB
from core.decorators import instance, command, timerevent
from core.setting_service import SettingService
from core.text import Text
from modules.standard.raid.item_types import LootItem, AuctionItem
from modules.standard.raid.leader_controller import LeaderController


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
        self.items_controller = registry.get_instance("items_controller")

    @command(command="loot", params=[], description="Show the list of added items", access_level="all")
    def loot_cmd(self, request):
        if not self.loot_list:
            return "Loot list is empty."

        if isinstance(list(self.loot_list.values())[0], AuctionItem):
            return self.get_auction_list()
        if isinstance(list(self.loot_list.values())[0], LootItem):
            return self.get_loot_list()

        return "Error when generating list (loot type is unsupported)."

    @command(command="loot", params=[Const("clear")], description="Clear all loot", access_level="all", sub_command="modify")
    def loot_clear_cmd(self, request, _):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

        if self.loot_list:
            self.loot_list.clear()
            self.last_modify = None
            return "Loot list cleared."
        else:
            return "Loot list is already empty."

    @command(command="loot", params=[Const("remitem"), Int("item_index")],
             description="Remove an existing loot item", access_level="all", sub_command="modify")
    def loot_rem_item_cmd(self, request, _, item_index: int):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

        if not self.loot_list:
            return "Loot list is empty."

        try:
            if self.loot_list[item_index]:
                self.last_modify = int(time.time())
                return "Removed %s from loot list." % self.loot_list.pop(item_index).get_item_str()
            else:
                return "Item error."
        except KeyError:
            return "Wrong index given."

    @command(command="loot", params=[Const("increase"), Int("item_index")], description="Increase item count",
             access_level="all", sub_command="modify")
    def loot_increase_item_cmd(self, request, _, item_index: int):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

        if not self.loot_list:
            return "Loot list is empty."

        try:
            loot_item = self.loot_list[item_index]

            if loot_item:
                loot_item.count += 1
                self.last_modify = int(time.time())
                return "Increased item count for %s to %d." % (loot_item.get_item_str(), loot_item.count)
            else:
                return "Item error."
        except KeyError:
            return "Wrong index given."

    @command(command="loot", params=[Const("decrease"), Int("item_index")], description="Decrease item count",
             access_level="all", sub_command="modify")
    def loot_decrease_item_cmd(self, request, _, item_index: int):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

        if not self.loot_list:
            return "Loot list is empty."

        try:
            loot_item = self.loot_list[item_index]

            if loot_item:
                loot_item.count = loot_item.count - 1 if loot_item.count > 1 else 1
                self.last_modify = int(time.time())
                return "Decreased item count for %s to %d." % (loot_item.get_item_str(), loot_item.count)
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

            if old_item:
                if old_item.get_item_str() == loot_item.get_item_str():
                    name = "You have" if request.channel == "msg" else request.sender.name
                    return "%s already added to %s." % (name, loot_item.get_item_str())

                old_item.bidders.remove(request.sender.name)

            name = "You have" if request.channel == "msg" else request.sender.name
            loot_item.bidders.append(request.sender.name)

            self.last_modify = int(time.time())

            if old_item is not None:
                return "%s moved from %s to %s." % (name, old_item.get_item_str(), loot_item.get_item_str())
            else:
                return "%s added to %s." % (name, loot_item.get_item_str())

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

                return "%s removed from %s." % (name, loot_item.get_item_str())
            else:
                return "You are not added to any loot."
        except KeyError:
            return "Wrong index given."

    @command(command="loot", params=[Const("roll")], description="Roll all loot", access_level="all", sub_command="modify")
    def loot_roll_cmd(self, request, _):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

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

                    blob += "%d. %s\n" % (i, loot_item.get_item_str())
                    blob += " | Winners: <red>%s<end>\n\n" % '<end>, <red>'.join(winners)

            return ChatBlob("Roll results", blob) if len(blob) > 0 else "No one was added to any loot"
        else:
            return "No loot to roll."

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

            return "List has been rebuilt." if len(self.loot_list) > 0 else "No items left to roll."
        else:
            return "Loot list is empty."

    @command(command="loot", params=[Const("addraiditem"), Int("raid_item_id"), Int("item_count")],
             description="Add item from pre-defined raid to loot list", access_level="all", sub_command="modify")
    def loot_add_raid_item(self, request, _, raid_item_id: int, item_count: int):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

        sql = "SELECT * FROM aodb a LEFT JOIN raid_loot r ON (a.name = r.name AND a.highql >= r.ql) " \
              "WHERE r.id = ? LIMIT 1"
        item = self.db.query_single(sql, [raid_item_id])

        if item:
            self.add_item_to_loot(item, item.comment, item_count)

            return "Added %s to loot list." % item.name
        else:
            return "Failed to add item with ID %s." % raid_item_id

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

            return "%s table was added to loot." % category
        else:
            return "%s does not have any items registered in loot table." % category

    @command(command="loot", params=[Const("additem", is_optional=True), Int("item"), Int("item_count", is_optional=True)],
             description="Add an item to loot list by item id", access_level="all", sub_command="modify")
    def loot_add_item_id_cmd(self, request, _, item_id, item_count: int):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

        if item_count is None:
            item_count = 1

        item = self.items_controller.get_by_item_id(item_id)
        if not item:
            return "Could not find item with ID <highlight>%d<end>." % item_id

        self.add_item_to_loot(item, None, item_count)

        return "%s was added to loot list." % item.name

    @command(command="loot", params=[Const("additem", is_optional=True), Item("item"), Int("item_count", is_optional=True)],
             description="Add an item to loot list by item_ref", access_level="all", sub_command="modify")
    def loot_add_item_ref_cmd(self, request, _, item, item_count: int):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

        if item_count is None:
            item_count = 1

        self.add_item_to_loot(item, None, item_count)

        return "%s was added to loot list." % item.name

    @command(command="loot", params=[Const("additem", is_optional=True), Any("item"), Int("item_count", is_optional=True)],
             description="Add an item to loot list", access_level="all", sub_command="modify")
    def loot_add_item_cmd(self, request, _, item, item_count: int):
        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG

        if item_count is None:
            item_count = 1

        self.add_item_to_loot(item, None, item_count)

        return "<highlight>%s<end> was added to loot list." % item

    @timerevent(budatime="1h", description="Periodically check when loot list was last modified, and clear it if last modification was done 1+ hours ago")
    def loot_clear_event(self, _1, _2):
        if self.loot_list and self.last_modify:
            if int(time.time()) - self.last_modify > 3600 and self.loot_list:
                self.last_modify = None
                self.loot_list = OrderedDict()
                self.bot.send_org_message("Loot was last modified more than 1 hour ago, list has been cleared.")
                self.bot.send_private_channel_message("Loot was last modified more than 1 hour ago, list has been cleared.")

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

            self.loot_list[end_index] = LootItem(item, comment, None, None, item_count)

        self.last_modify = int(time.time())

    def get_loot_list(self):
        blob = ""

        for i, loot_item in self.loot_list.items():
            bidders = loot_item.bidders

            increase_link = self.text.make_chatcmd("+", "/tell <myname> loot increase %d" % i)
            decrease_link = self.text.make_chatcmd("-", "/tell <myname> loot decrease %d" % i)

            blob += "%d. %s " % (i, loot_item.get_item_str())
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
            bidders = loot_item.bidders

            prefix = "" if loot_item.prefix is None else "%s " % loot_item.prefix
            suffix = "" if loot_item.suffix is None else " %s" % loot_item.suffix
            blob += "%d. %s%s%s\n" % (i, prefix, loot_item.get_item_str(), suffix)

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
                    "Where you replace &lt;amount&gt; with the amount of points you are welling to bid " \
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
