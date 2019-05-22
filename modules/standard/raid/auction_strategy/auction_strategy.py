import time

from core.chat_blob import ChatBlob
from core.registry import Registry
from core.sender_obj import SenderObj


class AuctionBid:
    def __init__(self, sender: SenderObj, account, current_amount, max_amount):
        self.sender = sender
        self.account = account
        self.current_amount = current_amount
        self.max_amount = max_amount

    def __str__(self):
        return self.__dict__.__str__()


class AuctionStrategy:
    def __init__(self):
        self.bot = Registry.get_instance("bot")
        self.db = Registry.get_instance("db")
        self.text = Registry.get_instance("text")
        self.alts_service = Registry.get_instance("alts_service")
        self.points_controller = Registry.get_instance("points_controller")
        self.job_scheduler = Registry.get_instance("job_scheduler")

        self.auction_start_time = None
        self.auction_end_time = None
        self.announce_interval = None
        self.is_started = False
        self.items = dict()
        self.winning_bids = dict()
        self.next_item_index = 1
        self.auctioneer: SenderObj = None
        self.job_id = None
        self.is_running = False

    def start(self, sender: SenderObj, duration, announce_interval):
        if not self.items:
            return "Could not find any items to start auction."

        self.is_started = True
        self.auction_start_time = int(time.time())
        self.auctioneer = sender
        self.auction_end_time = self.auction_start_time + duration
        self.is_running = True
        self.announce_interval = announce_interval

        if len(self.items) > 1:
            self.spam_raid_message("%s just started a mass auction for %d items." % (sender.name, len(self.items)))
            self.spam_raid_message(self.get_auction_list())
        else:
            item_index = list(self.items.keys())[0]
            item = self.items[item_index]
            sql = "SELECT winning_bid FROM auction_log WHERE item_name LIKE ? ORDER BY time DESC LIMIT 5"
            bids = self.db.query(sql, [item])
            if bids:
                avg_win_bid = int(sum(map(lambda x: x.winning_bid, bids)) / len(bids))
            else:
                avg_win_bid = 0

            bid_link = self.get_auction_list()
            bid_link = self.text.paginate_single(ChatBlob("Click to bid", bid_link.msg))
            msg = "\n<yellow>----------------------------------------<end>\n"
            msg += "<yellow>%s<end> has just started an auction " \
                   "for <yellow>%s<end>.\n" % (sender.name, item)
            msg += "Average winning bid: <highlight>%s<end>\n" % avg_win_bid
            msg += "%s\n" % bid_link
            msg += "<yellow>----------------------------------------<end>"

            self.spam_raid_message(msg)

        self.create_next_announce_job()

    def cancel(self, sender: SenderObj):
        self.cancel_job()
        self.is_running = False
        return "Auction cancelled."

    def add_item(self, item):
        self.items[self.next_item_index] = item
        self.next_item_index += 1
        return self.next_item_index

    def remove_item(self, item_id):
        # TODO will this fail if it doesn't exist
        del self.items[item_id]
        del self.winning_bids[item_id]

    def add_bid(self, sender: SenderObj, bid_amount, item_index):
        item_index = item_index or 1
        item = self.items.get(item_index, None)
        if not item:
            return "No item at given index."

        main_id = self.alts_service.get_main(sender.char_id).char_id
        account = self.points_controller.get_account(main_id)
        if not account:
            return "You do not have an active account with this bot."
        elif account.disabled:
            return "Your account has been frozen. Contact an admin."

        points_used = self.get_points_used(main_id, item_index)
        points_available = account.points - points_used

        if not bid_amount:
            return "You must specify an amount to bid."

        if isinstance(bid_amount, str) and bid_amount.lower() == "all":
            bid_amount = points_available

        # TODO handle when they are raising their own winning bid
        if bid_amount > points_available:
            return "You do not have enough points to make this bid. You have <highlight>%d<end> points available (<highlight>%d<end> points on account, <highlight>%d<end> points reserved for other bids)." \
                   % (points_available, points_available, points_used)

        current_amount = 0
        winning_bid = self.winning_bids.get(item_index, None)
        if winning_bid:
            if bid_amount <= winning_bid.current_amount:
                return "Your bid of <highlight>%d<end> points was not enough. <highlight>%s<end> is currently winning with a bid of <highlight>%d<end>." % (bid_amount, winning_bid.sender.name, winning_bid.current_amount)
            elif bid_amount <= winning_bid.max_amount:
                winning_bid.current_amount = bid_amount
                return "Your bid of <highlight>%d<end> points was not enough. <highlight>%s<end> is currently winning with a bid of <highlight>%d<end>." % (bid_amount, winning_bid.sender.name, winning_bid.current_amount)
            else:
                current_amount = winning_bid.max_amount
                self.bot.send_private_message(winning_bid.sender.char_id, "Your bid on %s has been overtaken by <highlight>%s<end>." % (item, sender.name))

        # increment 1 past current max bid
        current_amount += 1
        self.winning_bids[item_index] = AuctionBid(sender, account, current_amount, bid_amount)
        self.spam_raid_message("<highlight>%s<end> now holds the leading bid for %s with a bid of <highlight>%d<end>." % (sender.name, item, current_amount))
        return "Your max bid of <highlight>%d<end> points for %s has put you in the lead. " \
               "You have <highlight>%d<end> points left for bidding." % (bid_amount, item, points_available - bid_amount)

    def end(self):
        self.cancel_job()
        self.is_running = False

        blob = ""
        t = int(time.time())
        sql = "INSERT INTO auction_log (item_ref, item_name, winner_id, auctioneer_id, time, winning_bid, second_highest_bid) VALUES (?,?,?,?,?,?,?)"
        for i, item in self.items.items():
            winning_bid = self.winning_bids.get(i, None)
            if winning_bid:
                self.db.exec(sql, [item, item, winning_bid.sender.char_id, self.auctioneer.char_id, t, winning_bid.current_amount, 0])

                blob += "%d. %s, won by <highlight>%s<end> with <green>%d<end> points\n" % (i, item, winning_bid.sender.name, winning_bid.current_amount)
                main_id = self.alts_service.get_main(winning_bid.sender.char_id).char_id
                account = self.points_controller.get_account(main_id)
                self.points_controller.alter_points(account.points, main_id, -winning_bid.current_amount, self.auctioneer.char_id, "Won auction for %s" % item)
            else:
                blob += "%d. %s, no bids made\n" % (i, item)

        result_blob = ChatBlob("Auction results", blob)

        self.spam_raid_message(result_blob)

    def remove_bid(self, char_id, item_id):
        pass

    def spam_raid_message(self, message):
        self.bot.send_private_channel_message(message, fire_outgoing_event=False)
        self.bot.send_org_message(message, fire_outgoing_event=False)

    def get_auction_list(self):
        # TODO handle formatting when auction has finished

        blob = ""

        for i, item in self.items.items():
            blob += "%d. %s\n" % (i, item)

            winning_bid = self.winning_bids.get(i, None)
            if winning_bid:
                blob += " | <highlight>%s<end> has the winning bid of <highlight>%d<end>\n\n" % (winning_bid.sender.name, winning_bid.current_amount)
            else:
                blob += " | <green>No bidders<end>\n\n"

        return ChatBlob("Auction list (%d)" % len(self.items), blob)

    def get_points_used(self, main_id, item_index):
        points_used = 0
        for index, bid in self.winning_bids.items():
            if index != item_index and bid.account.char_id == main_id:
                points_used += bid.max_amount

        return points_used

    def auction_announce(self, t):
        time_left = self.time_left()
        if time_left <= 0:
            self.end()
            return

        item_count = len(self.items)
        if item_count > 1:
            msg = "Auction for %d items running. %d seconds left of auction." % (item_count, time_left)
        else:
            item_index = list(self.items.keys())[0]
            item = self.items[item_index]
            winning_bid = self.winning_bids.get(item_index, None)

            if winning_bid:
                winner = "<highlight>%s<end> now holds the leading bid with a bid of <highlight>%d<end>." % (winning_bid.sender.name, winning_bid.current_amount)
            else:
                winner = "No bids made."

            msg = "Auction for %s running. %s <highlight>%d<end> seconds left of auction." % (item, winner, time_left)

        self.spam_raid_message(msg)
        self.spam_raid_message(self.get_auction_list())
        self.create_next_announce_job()

    def time_left(self):
        t = int(time.time())
        time_left = self.auction_end_time - t
        if time_left < 0:
            time_left = 0

        return time_left

    def create_next_announce_job(self):
        t = int(time.time())
        time_remaining = self.auction_end_time - t
        mod = time_remaining % self.announce_interval
        if mod == 0:
            mod = self.announce_interval

        next_job_t = t + mod
        self.job_id = self.job_scheduler.scheduled_job(self.auction_announce, next_job_t)

    def cancel_job(self):
        if self.job_id:
            self.job_scheduler.cancel_job(self.job_id)
            self.job_id = None
