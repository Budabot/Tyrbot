import secrets
import time
from collections import OrderedDict

from core.chat_blob import ChatBlob
from core.command_param_types import Options, Const, Int, Item, Any
from core.db import DB
from core.decorators import instance, command, setting, timerevent
from core.setting_service import SettingService
from core.setting_types import BooleanSettingType
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
        self.settings_service: SettingService = registry.get_instance("setting_service")
        self.text: Text = registry.get_instance("text")
        self.leader_controller: LeaderController = registry.get_instance("leader_controller")
        self.setting_service: SettingService = registry.get_instance("setting_service")

    @setting(name="use_item_icons", value="True", description="Use icons when building loot list")
    def use_item_icons(self):
        return BooleanSettingType()

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
        else:
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
        else:
            return "%s does not have any items registered in loot table." % category

    @command(command="apf",
             params=[Options(["s7", "s13", "s28", "s35"], is_optional=True)],
             description="Get list of items from APF", access_level="all")
    def apf_cmd(self, _, category):
        if category is None:
            blob = ""
            sql = "SELECT category FROM raid_loot WHERE raid = 'APF' GROUP BY category"
            raids = self.db.query(sql)

            for raid in raids:
                add_loot = self.text.make_chatcmd("Add loot", "/tell <myname> loot addraid APF %s" % raid.category)
                show_loot = self.text.make_chatcmd(
                    "Loot table", "/tell <myname> apf %s" % self.get_real_category_name(raid.category, True))

                sql = "SELECT COUNT(*) AS count FROM raid_loot WHERE category = ?"
                count = self.db.query_single(sql, [raid.category]).count

                blob += "%s - %s items\n" % (raid.category, count)
                blob += " | [%s] [%s]\n\n" % (show_loot, add_loot)

            return ChatBlob("APF loot tables", blob)

        add_all = True if category != "s7" else False
        category = self.get_real_category_name(category)

        items = self.get_items("APF", category)

        if items:
            return ChatBlob("%s loot table" % category, self.build_list(items, "APF", category, add_all))
        else:
            return "No loot registered for <highlight>%s<end>." % category

    @command(command="pande",
             params=[
                 Options(["bweapons", "barmor", "bstars", "aries", "aqua", "leo",
                          "virgo", "cancer", "gemini", "libra", "pisces", "capri",
                          "scorpio", "taurus", "sagi"], is_optional=True)
             ],
             description="Get list of items from Pandemonium", access_level="all")
    def pande_cmd(self, _, category):
        if category is None:
            blob = ""
            sql = "SELECT category FROM raid_loot WHERE raid = 'Pande' GROUP BY category"
            raids = self.db.query(sql)

            for raid in raids:
                show_loot = self.text.make_chatcmd(
                    "Loot table", "/tell <myname> pande %s" % self.get_real_category_name(raid.category, True))

                sql = "SELECT COUNT(*) AS count FROM raid_loot WHERE category = ?"
                count = self.db.query_single(sql, [raid.category]).count

                blob += "%s - %s items\n" % (raid.category, count)
                blob += " | [%s]\n\n" % show_loot

            return ChatBlob("Pandemonium loot tables", blob)

        category = self.get_real_category_name(category)

        items = self.get_items("Pande", category)

        if items:
            return ChatBlob("%s loot table" % category, self.build_list(items, "Pande", category))
        else:
            return "No loot registered for <highlight>%s<end>." % category

    @command(command="db", params=[Options(["db1", "db2", "db3", "dbarmor", "util"], is_optional=True)],
             description="Get list of items from DustBrigade", access_level="all")
    def db_cmd(self, _, category):
        if category is None:
            blob = ""
            sql = "SELECT category FROM raid_loot WHERE raid = 'DustBrigade' GROUP BY category"
            raids = self.db.query(sql)

            for raid in raids:
                show_loot = self.text.make_chatcmd("Loot table", "/tell <myname> db %s" % self.get_real_category_name(raid.category, True))

                sql = "SELECT COUNT(*) AS count FROM raid_loot WHERE category = ?"
                count = self.db.query_single(sql, [raid.category]).count

                blob += "%s - %s items\n" % (raid.category, count)
                blob += " | [%s]\n\n" % show_loot

            return ChatBlob("DustBrigade loot tables", blob)

        category = self.get_real_category_name(category)

        items = self.get_items("DustBrigade", category)

        if items:
            return ChatBlob("%s loot table" % category, self.build_list(items, "DustBrigade", category))
        else:
            return "No loot registered for <highlight>%s<end>." % category

    @command(command="xan", params=[Options(["mitaar", "12m", "vortexx"], is_optional=True)],
             description="Get list of items from Xan", access_level="all")
    def xan_cmd(self, _, category):
        if category is None:
            blob = ""
            raids = ["Mitaar", "Vortexx", "12Man"]

            for raid in raids:
                show_loot = self.text.make_chatcmd(
                    "Loot table", "/tell <myname> xan %s" % self.get_real_category_name(category, True))

                sql = "SELECT COUNT(*) AS count FROM raid_loot WHERE raid = ?"
                count = self.db.query_single(sql, [raid]).count

                blob += "%s - %s items\n" % (raid, count)
                blob += " | [%s]\n\n" % show_loot

            return ChatBlob("Xan loot tables", blob)

        category = self.get_real_category_name(category)

        blob = ""

        blob += self.build_list(self.get_items(category, "General"), category, "General")

        blob += self.build_list(self.get_items(category, "Symbiants"), category, "Symbiants")

        blob += self.build_list(self.get_items(category, "Spirits"), category, "Spirits")

        if category == "12Man":
            blob += self.build_list(self.get_items(category, "Profession Gems"), category, "Profession Gems")

        return ChatBlob("%s loot table" % category, blob)

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

    # Raids available in AO:
    # s7, s10, s13, s28, s35, s42, aquarius, virgo, sagittarius, beastweapons, beastarmor,
    # beaststars, tnh, aries, leo, cancer, gemini, libra, pisces, taurus,
    # capricorn, scorpio, tara, vortexx, mitaar, 12m, db1, db2, db3, poh,
    # biodome, manex (collector), hollow islands, mercenaries

    def build_list(self, items, raid=None, category=None, add_all=False):
        blob = ""

        if add_all:
            blob += "%s items to loot list\n\n" % self.text.make_chatcmd(
                "Add all", "/tell <myname> loot addraid %s %s" % (raid, category))

        blob += "<header2>%s<end>\n" % category if category is not None else ""

        for item in items:
            item_ref = "raid %d" % item.id

            if item.multiloot > 1:
                single_link = self.text.make_chatcmd("Add x1", "/tell <myname> loot additem %s 1" % item_ref)
                multi_link = self.text.make_chatcmd(
                    "Add x%d" % item.multiloot, "/tell <myname> loot additem %s %d" % (item_ref, item.multiloot))
                add_links = "[%s] [%s]" % (single_link, multi_link)
            else:
                add_links = "[%s]" % self.text.make_chatcmd("Add x1", "/tell <myname> loot additem %s 1" % item_ref)

            comment = " (%s)" % item.comment if item.comment != "" else ""

            if self.settings_service.get("use_item_icons").get_value():
                item_link = self.text.make_item(item.lowid, item.highid, item.ql, "<img src=rdb://%s>" % item.icon)
                blob += "%s\n%s%s\n | %s\n\n" % (item_link, item.name, comment, add_links)
            else:
                item_link = self.text.make_item(item.lowid, item.highid, item.ql, item.name)
                blob += "%s%s\n | %s\n\n" % (item_link, comment, add_links)

        return blob

    def get_items(self, raid, category):
        return self.db.query(
            "SELECT r.raid, r.category, r.id, r.ql, r.name, r.comment, r.multiloot, a.lowid, a.highid, a.icon "
            "FROM raid_loot r "
            "LEFT JOIN aodb a "
            "ON (r.name = a.name AND r.ql <= a.highql) "
            "WHERE r.raid = ? AND r.category = ? "
            "ORDER BY r.name",
            [raid, category]
        )

    def get_real_category_name(self, category, reverse=False):
        real_names = {
            "s7": "Sector 7", "s13": "Sector 13", "s28": "Sector 28", "s35": "Sector 35",
            "s42": "Sector 42", "db": "DustBrigade", "aqua": "Aquarius", "sagi": "Sagittarius",
            "saggi": "Sagittarius", "taurus": "Taurus", "libra": "Libra", "capri": "Capricorn",
            "gemini": "Gemini", "virgo": "Virgo", "cancer": "Cancer", "pisces": "Pisces",
            "scorpio": "Scorpio", "aries": "Aries", "leo": "Leo", "tnh": "The Night Heart",
            "barmor": "Beast Armor", "beastweapons": "Beast Weapons", "bstars": "Stars",
            "alba": "Albtraum", "symbs": "Symbiants", "spirits": "Spirits",
            "pgems": "Profession Gems", "gen": "General", "db1": "DB1", "db2": "DB2",
            "db3": "DB3", "ncu": "HUD/NCU", "gaunt": "Bastion", "mitaar": "Mitaar",
            "12m": "12Man", "vortexx": "Vortexx", "dbarmor": "DB Armor", "util": "Util"
        }

        if reverse:
            return next((name for name, real_name in real_names.items() if real_name == category), None)
        else:
            return real_names[category] if category in list(real_names.keys()) else None
