from core.db import DB
from core.dict_object import DictObject
from core.text import Text
from core.tyrbot import Tyrbot
from core.decorators import command, instance, setting
from core.command_param_types import Const, Options, Int, Any
from core.chat_blob import ChatBlob
from core.setting_types import BooleanSettingType, NumberSettingType
from core.setting_service import SettingService
from core.lookup.character_service import CharacterService
from core.alts.alts_service import AltsService
from core.job_scheduler import JobScheduler
from modules.standard.raid.loot_controller import LootController
from .points_controller import PointsController
from .item_types import AuctionItem
import re
import time
import secrets


class BidderAccount:
    def __init__(self, main_id, bidder_id, points_available):
        self.main_id = main_id
        self.bidder_id = bidder_id
        self.points_available = points_available
        self.points_used = 0


class AuctionBid:
    def __init__(self, char_id, bid):
        self.char_id = char_id
        self.bid = bid
        self.bid_count = 0


@instance()
class AuctionController:
    def __init__(self):
        self.auction_running = False
        self.auction_time = None
        self.ignore = False
        self.bidder_accounts = {}
        self.announce_ids = []
        self.announe_anti_ids = []
        self.auction_anti_spam = []

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.bot: Tyrbot = registry.get_instance("bot")
        self.loot_controller: LootController = registry.get_instance("loot_controller")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.job_scheduler: JobScheduler = registry.get_instance("job_scheduler")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.alts_service: AltsService = registry.get_instance("alts_service")
        self.points_controller: PointsController = registry.get_instance("points_controller")

    @setting(name="vickrey_auction", value=False,
             description="If true, the auction procedure will be done in the Vickrey approach")
    def vickrey_auction(self):
        return BooleanSettingType()

    @setting(name="minimum_bid", value="2", description="Minimum bid required for any bid to be valid")
    def minimum_bid(self):
        return NumberSettingType()

    @setting(name="auction_length", value="90", description="Regular auction length in seconds")
    def auction_length(self):
        return NumberSettingType()

    @setting(name="auction_announce_interval", value="15", description="Auction announce interval")
    def auction_announce_interval(self):
        return NumberSettingType()

    @setting(name="mass_auction_length", value="180", description="Mass auction length in seconds")
    def mass_auction_length(self):
        return NumberSettingType()

    @setting(name="mass_auction_announce_interval", value="30", description="Mass auction announce interval")
    def mass_auction_announce_interval(self):
        return NumberSettingType()

    @command(command="auction", params=[Const("start"), Any("items")],
             description="Start an auction, with one or more items", access_level="moderator")
    def auction_start_cmd(self, request, _, items):
        if self.auction_running:
            return "Auction already running."

        items = re.findall(r"(([^<]+)?<a href=\"itemref://(\d+)/(\d+)/(\d+)\">([^<]+)</a>([^<]+)?)", items)

        if items:
            auction_item = None
            for item in items:
                _, prefix, low_id, high_id, ql, name, suffix = item
                auction_item = self.add_auction_item_to_loot(int(low_id), int(high_id), int(ql),
                                                             name, request.sender.char_id, prefix, suffix, 1)

            if len(self.loot_controller.loot_list) > 1:
                self.bot.send_org_message("%s just started a mass auction "
                                          "for %d items." % (request.sender.name, len(self.loot_controller.loot_list)))
                self.bot.send_private_channel_message(
                    "%s just started a mass auction for %d items." % request.sender.name,
                    len(self.loot_controller.loot_list))
                self.loot_controller.loot_cmd(request)
            else:
                sql = "SELECT winning_bid FROM auction_log WHERE " \
                      "item_name LIKE '%' || ? || '%' ORDER BY time DESC LIMIT 5"
                bids = self.db.query(sql, [auction_item.item.name])
                if bids:
                    avg_win_bid = int(sum(map(lambda x: x.winning_bid, bids)) / len(bids))
                else:
                    avg_win_bid = 0

                bid_link = self.loot_controller.get_auction_list()
                bid_link = self.text.paginate(ChatBlob("Click to bid", bid_link.msg), 5000, 1)[0]
                msg = "\n<yellow>----------------------------------------<end>\n"
                msg += "<yellow>%s<end> has just started an auction " \
                       "for <yellow>%s<end>.\n" % (request.sender.name, auction_item.item.name)
                msg += "Average winning bid: <highlight>%s<end>\n" % avg_win_bid
                msg += "%s\n" % bid_link
                msg += "<yellow>----------------------------------------<end>"

                self.bot.send_private_channel_message(msg)
                self.bot.send_org_message(msg)

            self.auction_running = True
            self.auction_time = int(time.time())
            self.create_auction_timers()

        else:
            return "Can't start empty auction."

    @command(command="auction", params=[Options(["cancel", "end"])], description="Cancel ongoing auction",
             access_level="moderator")
    def auction_cancel_cmd(self, _1, _2):
        if self.auction_running:
            self.auction_running = False
            self.auction_time = None
            self.loot_controller.loot_list.clear()
            self.bidder_accounts.clear()

            for announce_id in self.announce_ids:
                self.job_scheduler.cancel_job(announce_id)

            for announce_id in self.announe_anti_ids:
                self.job_scheduler.cancel_job(announce_id)

            self.announce_ids.clear()
            self.announe_anti_ids.clear()
            self.auction_anti_spam.clear()

            return "Auction canceled."

        return "No auction running."

    @command(command="auction", params=[Const("bid"),
                                        Int("amount", is_optional=True),
                                        Const("all", is_optional=True),
                                        Int("item_index", is_optional=True)],
             description="Bid on an item", access_level="member", sub_command="bid")
    def auction_bid_cmd(self, request, _, amount, all_amount, item_index):
        if not self.auction_running:
            return "No auction in progress."

        if amount or all_amount:
            vickrey = self.setting_service.get("vickrey_auction").get_value()
            minimum_bid = self.setting_service.get("minimum_bid").get_value()
            main_id = self.alts_service.get_main(request.sender.char_id).char_id
            item_index = item_index or 1
            new_bidder = False

            try:
                auction_item = self.loot_controller.loot_list[item_index]
            except KeyError:
                return "No item at given index."

            try:
                bidder_account = self.bidder_accounts[main_id]
                t_available = bidder_account.points_available
            except KeyError:
                sql = "SELECT p.points, p.disabled FROM points p WHERE p.char_id = ?"
                t_available = self.db.query_single(sql, [main_id])

                if t_available:
                    if t_available.disabled > 0:
                        return "Your account has been frozen. Contact an admin."

                    t_available = t_available.points
                else:
                    return "You do not have an active account with this bot."

                self.bidder_accounts[main_id] = BidderAccount(main_id, request.sender.char_id, t_available)
                bidder_account = self.bidder_accounts[main_id]

            bidder = next((bidder for bidder in auction_item.bidders if bidder.char_id == request.sender.char_id), None)

            if bidder:
                used = bidder_account.points_used - bidder.bid
                available = t_available - used
            else:
                new_bidder = True
                available = t_available
                used = 0
                bidder = AuctionBid(request.sender.char_id, amount)

            if all_amount:
                amount = available

            if amount > available:
                return "You do not have enough points to make this bid. You have %d points " \
                       "available (%d points on account, %d points reserved for other bids)" \
                       % (available, t_available, used)

            if amount < minimum_bid:
                return "Invalid bid. The minimum allowed bid value is %d." % minimum_bid

            if vickrey:
                if bidder.bid_count < 2:
                    if bidder.bid == amount and not new_bidder:
                        return "The submitted bid matches your current bid. You can only submit a " \
                               "new bid if it's of higher value than the previous bid. This bid did not " \
                               "count against your bid count for this item."
                    if bidder.bid > amount:
                        return "The submitted bid is lower than your current bid. You can only submit a " \
                               "new bid if it's of higher value than the previous bid. This bid did not " \
                               "count against your bid count for this item."

                    bidder.bid_count += 1
                    bidder.bid = amount
                    bidder_account.points_used = used + amount
                    auction_item.second_highest = auction_item.winning_bid \
                        if auction_item.winning_bid > 0 else minimum_bid
                    auction_item.winning_bid = amount
                    auction_item.winner_id = bidder.char_id
                    if new_bidder:
                        auction_item.bidders.append(bidder)

                    bid_count_text = "first" if bidder.bid_count == 1 else "second"
                    return "Your bid of %d points was accepted. This was your %s bid on " \
                           "this item. You have %d points left to use in the ongoing " \
                           "auction." % (amount, bid_count_text, (available - amount))
                else:
                    return "You've already exhausted your allowed bids for this item; as this " \
                       "is a Vickrey auction, you only get to bid twice on the same item."
            else:
                winner_name = self.character_service.resolve_char_to_name(auction_item.winner_id)
                bidder_name = self.character_service.resolve_char_to_name(request.sender.char_id)
                item_name = auction_item.item.name

                if bidder.bid > auction_item.second_highest:
                    auction_item.second_highest = bidder.bid

                if bidder.bid <= auction_item.winning_bid:
                    self.auction_anti_spam.append("%s's bid of <red>%d<end> points did not exceed the "
                                                  "current winning bid for %s. %s holds the winning bid."
                                                  % (bidder_name, bidder.bid, item_name, winner_name))
                    return "Your bid of %d points was not enough. %s is currently " \
                           "winning with a minimum bid of %d." % (bidder.bid, winner_name, auction_item.second_highest)

                if bidder.bid > auction_item.winning_bid:
                    if auction_item.winner_id:
                        prev_main_id = self.alts_service.get_main(auction_item.winner_id).char_id
                        prev_bidder_account = self.bidder_accounts[prev_main_id]
                        # print("tot: %d -- used: %d" % (prev_bidder_account.points_available, prev_bidder_account.points_used))
                        prev_bidder_account.points_used -= auction_item.winning_bid
                        # print("tot: %d -- used: %d" % (prev_bidder_account.points_available, prev_bidder_account.points_used))
                        new_available = prev_bidder_account.points_available - prev_bidder_account.points_used
                        # print("tot: %d -- used: %d -- new avail: %d" % (prev_bidder_account.points_available, prev_bidder_account.points_used, new_available))
                        self.bot.send_private_message(
                            auction_item.winner_id,
                            "Your bid on %s has been overtaken by %s. The points have been returned to your pool of "
                            "available points (%d points)." % (item_name, bidder_name, new_available))

                    auction_item.second_highest = auction_item.winning_bid + 1
                    if auction_item.second_highest == 0:
                        auction_item.second_highest = minimum_bid

                    auction_item.winning_bid = bidder.bid
                    auction_item.winner_id = bidder.char_id

                    if new_bidder:
                        auction_item.bidders.append(bidder)

                    bidder_account.points_used = used + amount
                    new_available = t_available - bidder_account.points_used
                    if len(self.announce_ids) < 2 and len(self.loot_controller.loot_list) == 1:
                        self.job_scheduler.cancel_job(self.announce_ids.pop())
                        self.announce_ids.append(self.job_scheduler.delayed_job(self.auction_results, 10))
                        self.bot.send_org_message("%s now holds the leading bid for %s. Bid was "
                                                  "made with less than 10 seconds left of auction, end timer has "
                                                  "been pushed back 10 seconds." % (bidder_name, item_name))
                        self.bot.send_private_channel_message("%s now holds the leading bid for %s. Bid was made with "
                                                              "less than 10 seconds left of auction, end timer has been"
                                                              " pushed back 10 seconds." % (bidder_name, item_name))
                    else:
                        self.auction_anti_spam.append("%s now holds the leading bid for %s." % (bidder_name, item_name))
                    return "Your bid of %d points for %s has put you in the lead. " \
                           "You have %d points available for bidding." % (bidder.bid, item_name, new_available)

        return "Invalid bid."

    @command(command="auction", params=[Const("bid"), Const("item"), Int("item_index")],
             description="Get bid info for a specific item", access_level="member", sub_command="bid_info")
    def auction_bid_info_cmd(self, _1, _2, _3, item_index):
        if not self.loot_controller.loot_list:
            return "No auction running."

        blob = ""

        loot_item = self.loot_controller.loot_list[item_index]
        ao_item = loot_item.item
        min_bid = self.setting_service.get("minimum_bid").get_value()

        blob += "To bid for <yellow>%s<end>, you must send a tell to <myname> with\n\n" % ao_item.name
        blob += "<highlight><tab>/tell <myname> auction bid &lt;amount&gt; %d<end>\n\n" % item_index
        blob += "Where you replace &lt;amount&gt; with the amount of points you're willing to bid for the item.\n"
        blob += "Minimum bid is %d. You can also use \"all\" as bid, to bid all your available points.\n\n" % min_bid
        blob += "<highlight>Please note<end> that if you leave out the trailing number, %d. " % item_index
        blob += "It determines the auction item number you're bidding on, "
        blob += "which can be noted on the loot list, in front of the item name.\n\n"
        if self.setting_service.get("vickrey_auction").get_value():
            blob += "<header2>This is a Vickrey auction<end>\n"
            blob += " - In a Vickrey auction, you only get to bid twice on the same item.\n"
            blob += " - You won't be notified of the outcome of your bid, as all bids will be anonymous.\n"
            blob += " - The highest anonymous bid will win, and pay the second-highest bid.\n"
            blob += " - Bids are anonymous; sharing your bid with others defeat the purpose of the Vickrey format.\n"
            blob += " - Bidding is done the same way as regular bids, as described above."

        return ChatBlob("Bid on item %s" % ao_item.name, blob)

    def add_auction_item_to_loot(self, low_id: int, high_id: int, ql: int,
                                 name: str, auctioneer_id: int, prefix=None, suffix=None, item_count=1):
        end_index = list(self.loot_controller.loot_list.keys())[-1]+1 if len(self.loot_controller.loot_list) > 0 else 1

        item_ref = DictObject({"low_id": low_id, "high_id": high_id, "ql": ql, "name": name})

        self.loot_controller.loot_list[end_index] = AuctionItem(item_ref, None, auctioneer_id, prefix, suffix, item_count)

        return self.loot_controller.loot_list[end_index]

    def create_auction_timers(self):
        if len(self.loot_controller.loot_list) > 1:
            auction_length = self.setting_service.get("mass_auction_length").get_value()
            interval = self.setting_service.get("mass_auction_announce_interval")
        else:
            auction_length = self.setting_service.get("auction_length").get_value()
            interval = self.setting_service.get("auction_announce_interval").get_value()

        iterations = int((auction_length - auction_length % interval) / interval)

        for i in range(1, iterations):
            iteration = i*interval
            time_left = int(auction_length - iteration)
            self.announce_ids.append(self.job_scheduler.delayed_job(self.auction_announce, iteration, time_left))

        for i in range(1, auction_length):
            self.announe_anti_ids.append(self.job_scheduler.delayed_job(self.auction_anti_spam_announce, i))

        if len(self.loot_controller.loot_list) == 1:
            self.announce_ids.append(self.job_scheduler.delayed_job(self.auction_results, auction_length))

    def auction_announce(self, _, time_left):
        if self.auction_running:
            self.announce_ids.pop(0)

            item_count = len(self.loot_controller.loot_list)

            if self.announce_ids and item_count > 1:
                msg = "Auction for %d items running. %d seconds left of auction." % (item_count, time_left)
            elif len(self.loot_controller.loot_list) > 1:
                msg = "Auction for %d items will end within 30 seconds" % item_count
                self.announce_ids.append(self.job_scheduler.delayed_job(self.auction_results,
                                                                        secrets.choice(range(5, 30))))
            else:
                auction_item = list(self.loot_controller.loot_list.values())[-1]
                item = auction_item.item

                if self.setting_service.get("vickrey_auction").get_value():
                    winner = "%d bid(s) have been made." % len(auction_item.bidders) \
                        if auction_item.bidders else "No bids made."
                else:
                    winner_name = self.character_service.resolve_char_to_name(auction_item.winner_id)
                    winner = "%s holds the winning bid." % winner_name \
                        if auction_item.winning_bid > 0 else "No bids made."

                item_ref = self.text.make_item(item.low_id, item.high_id, item.ql, item.name)
                msg = "Auction for %s running. %s " \
                      "<yellow>%d<end> seconds left of auction." % (item_ref, winner, time_left)

            self.bot.send_private_channel_message(msg)
            self.bot.send_org_message(msg)
            self.loot_controller.loot_cmd(None)

    def auction_anti_spam_announce(self, _):
        announce = None

        if len(self.auction_anti_spam) >= 1:
            announce = self.auction_anti_spam.pop(-1)
            self.auction_anti_spam.clear()

        if announce:
            self.bot.send_org_message(announce)
            self.bot.send_private_channel_message(announce)

    def auction_results(self, _):
        sql = "INSERT INTO auction_log (item_ref, item_name, winner_id, " \
              "auctioneer_id, time, winning_bid, second_highest_bid) VALUES (?,?,?,?,?,?,?)"

        blob = ""

        for i, auction_item in self.loot_controller.loot_list.items():
            was_rolled = False
            if self.setting_service.get("vickrey_auction").get_value():
                was_rolled = self.find_vickrey_winner(auction_item)

            item = auction_item.item
            item_ref = self.text.make_item(item.low_id, item.high_id, item.ql, item.name)
            prefix = "%s " % auction_item.prefix if auction_item.prefix is not None else ""
            suffix = " %s" % auction_item.suffix if auction_item.prefix is not None else ""
            item_name = "%s%s%s" % (prefix, item.name, suffix)

            if auction_item.winning_bid > 0:
                self.db.exec(sql, [item_ref, item_name, auction_item.winner_id, auction_item.auctioneer_id,
                                   int(time.time()), auction_item.winning_bid, auction_item.second_highest])

                winner_name = self.character_service.resolve_char_to_name(auction_item.winner_id)
                was_rolled = " (winner was determined by roll)" if was_rolled else ""
                blob += "%d. %s (ql%d), won by <yellow>%s<end> " \
                        "with <green>%d<end> points%s" \
                        % (i, item_ref, item.ql, winner_name, auction_item.second_highest, was_rolled)
                main_id = self.alts_service.get_main(auction_item.winner_id).char_id
                current_points = self.bidder_accounts[main_id].points_available
                self.points_controller.alter_points(current_points, main_id, -auction_item.second_highest,
                                                    auction_item.auctioneer_id, "Won auction for %s" % item_name)
            else:
                blob += "%d. %s (ql%d), no bids made" % (i, item_ref, item.ql)

        self.auction_running = False
        self.auction_time = None
        self.bidder_accounts.clear()
        self.announce_ids.clear()
        self.announe_anti_ids.clear()
        self.loot_controller.loot_list.clear()

        result_blob = ChatBlob("Auction results", blob)

        self.bot.send_org_message(result_blob)
        self.bot.send_private_channel_message(result_blob)

    def find_vickrey_winner(self, item: AuctionItem):
        was_rolled = False

        if item.bidders:
            minimum_bid = self.setting_service.get("minimum_bid").get_value()
            vickrey_list = []
            winning_bid = 0
            winner = None

            for bidder in item.bidders:
                if bidder.bid > winning_bid:
                    item.second_highest = winning_bid
                    winning_bid = bidder.bid
                    winner = bidder.char_id
                    vickrey_list.clear()
                elif bidder.bid == winning_bid and winner:
                    # Potential pitfall if winner for some strange reason is None.
                    # It should not be possible to do a bid of 0 or less, so we just
                    # assume that if bid is equal to winning bid, winning bid must be
                    # greater than 0, and thus a winner must exist from a previous
                    # iterated bid
                    vickrey_list.append(bidder.char_id)

            if vickrey_list:
                vickrey_list.append(winner)
                item.second_highest = winning_bid
                winner = secrets.choice(vickrey_list)
                was_rolled = True

            if winning_bid > 0 and winner:
                item.winning_bid = winning_bid
                item.winner_id = winner
                if item.second_highest == 0:
                    item.second_highest = minimum_bid

        return was_rolled
