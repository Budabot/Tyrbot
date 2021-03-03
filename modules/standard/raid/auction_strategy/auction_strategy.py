import time

from core.chat_blob import ChatBlob
from core.conn import Conn
from core.dict_object import DictObject
from core.registry import Registry
from core.sender_obj import SenderObj


class AuctionBid:
    def __init__(self, sender: SenderObj, account, max_amount, created_at):
        self.sender = sender
        self.account = account
        self.max_amount = max_amount
        self.created_at = created_at

    def __str__(self):
        return self.__dict__.__str__()

    def __repr__(self):
        return self.__str__()


class AuctionStrategy:
    def __init__(self, conn: Conn):
        self.bot = Registry.get_instance("bot")
        self.db = Registry.get_instance("db")
        self.text = Registry.get_instance("text")
        self.alts_service = Registry.get_instance("alts_service")
        self.points_controller = Registry.get_instance("points_controller")
        self.job_scheduler = Registry.get_instance("job_scheduler")
        self.raid_controller = Registry.get_instance("raid_controller")

        self.auction_start_time = None
        self.auction_end_time = None
        self.is_started = False
        self.items = dict()
        self.bids = DictObject()  # self.bids[item_index] = [AuctionBid(), AuctionBid()]
        self.next_item_index = 1
        self.auctioneer: SenderObj = None
        self.is_running = False
        self.conn = conn

    def start(self, sender: SenderObj, duration):
        if not self.items:
            return "Could not find any items to start auction."

        self.is_started = True
        self.auction_start_time = int(time.time())
        self.auctioneer = sender
        self.auction_end_time = self.auction_start_time + duration
        self.is_running = True

        self.announce()

    def cancel(self, sender: SenderObj):
        self.is_running = False
        return "Auction cancelled."

    def add_item(self, item):
        self.items[self.next_item_index] = item
        self.next_item_index += 1
        return self.next_item_index

    def remove_item(self, item_id):
        # TODO will this fail if it doesn't exist?
        del self.items[item_id]
        del self.bids[item_id]

    def add_bid(self, sender: SenderObj, bid_amount, item_index):
        if len(self.items) > 1 and not item_index:
            return "You must specify an item to bid on by its item number in the auction list."

        if not bid_amount:
            return "You must specify an amount to bid."

        item_index = item_index or 1
        item = self.items.get(item_index, None)
        if not item:
            return f"No item at index <highlight>{item_index}</highlight>."

        main_id = self.alts_service.get_main(sender.char_id).char_id
        account = self.points_controller.get_account(main_id, self.conn)
        if account.disabled:
            return "Your account has been disabled. Contact an admin."

        if isinstance(bid_amount, str) and bid_amount.lower() == "all":
            bid_amount = account.points

        if bid_amount > account.points:
            return "You cannot bid more than your maximum available points (<highlight>%d</highlight>)." % account.points

        if item_index not in self.bids:
            self.bids[item_index] = []

        current_bid = self.get_current_bid(main_id, item_index)
        if current_bid:
            current_bid.max_amount = bid_amount
            return f"Your bid amount has been changed to <highlight>{bid_amount}</highlight>."
        else:
            self.bids[item_index].append(AuctionBid(sender, account, bid_amount, time.time()))
            return "Your bid has been recorded successfully."

    def remove_bid(self, sender: SenderObj, item_index):
        if len(self.items) > 1 and not item_index:
            return "You must specify an item to remove your bid from by its item number in the auction list."

        item_index = item_index or 1
        item = self.items.get(item_index, None)
        if not item:
            return f"No item at index <highlight>{item_index}</highlight>."

        main_id = self.alts_service.get_main(sender.char_id).char_id

        if item_index not in self.bids:
            self.bids[item_index] = []

        for bid in self.bids[item_index]:
            if bid.account.char_id == main_id:
                self.bids[item_index].remove(bid)
                return "Your bid has been removed."

        return "You do not have a bid for this item."

    def end(self):
        if not self.is_running:
            return

        self.is_running = False

        blob = ""
        t = int(time.time())
        sql = "INSERT INTO auction_log (item_ref, item_name, winner_id, auctioneer_id, created_at, winning_bid) VALUES (?,?,?,?,?,?)"
        for i, item in self.items.items():
            # update max_amount values based on current account points
            bids = []
            for bid in (self.bids.get(i, [])):
                account = self.points_controller.get_account(bid.account.char_id, self.conn)
                if account.points == 0:
                    continue

                if bid.max_amount > account.points:
                    bid.max_amount = account.points

                bids.append(bid)

            bids = sorted(bids, key=lambda x: x.max_amount, reverse=True)

            count = len(bids)
            if count == 0:
                blob += "%d. %s, no bids made\n" % (i, item)
                continue

            if count == 1:
                winning_amount = 1
                winning_bid = bids[0]
            else:
                winning_bid = bids[0]
                winning_amount = bids[1].max_amount + 1
                for bid in bids[1:]:
                    if bid.max_amount == winning_bid.max_amount:
                        if bid.created_at < winning_bid.created_at:
                            winning_bid = bid
                    else:
                        break

                # if there is a tie
                if winning_amount > winning_bid.max_amount:
                    winning_amount = winning_bid.max_amount

            self.db.exec(sql, [item, item, winning_bid.sender.char_id, self.auctioneer.char_id, t, winning_amount])

            blob += "%d. %s, won by <highlight>%s</highlight> with <green>%d</green> points\n" % (i, item, winning_bid.sender.name, winning_amount)
            self.points_controller.alter_points(winning_bid.account.char_id, self.auctioneer.char_id, "Won auction for %s" % item, -winning_amount)

        self.spam_raid_message(ChatBlob("Auction results", blob))

    def spam_raid_message(self, message):
        self.raid_controller.send_message(message, self.conn)

    def get_auction_list(self):
        blob = ""

        for i, item in self.items.items():
            blob += "%d. %s\n" % (i, item)
            num_bids = len(self.bids.get(i, []))
            blob += f" └ {num_bids} bid(s)\n"
            blob += "\n"

        blob += "\n-----------------------\n" \
                "This bot uses a modified Vickrey system. It is a silent auction and winning bids are not announced until the end. " \
                "The highest bidder pays the amount of the second highest bidder plus 1. " \
                "If there is a tie for the highest bidder, the person who bid first wins and pays the full bid amount. If there is only one bidder " \
                "the winner pays 1. You should bid the maximum amount of points that you want to pay for an item. If you win, you will never pay more " \
                "than your maximum bid and oftentimes you will pay less. If you lose, you pay nothing.\n\n"
        blob += "To bid, use: !auction bid <highlight>&lt;amount&gt; &lt;item_number&gt;</highlight>\n\n"
        blob += "You can bid all of your points with: !auction bid all <highlight>&lt;item_number&gt;</highlight>"

        return ChatBlob("Auction list (%d)" % len(self.items), blob)

    def get_current_bid(self, main_id, item_index):
        for bid in self.bids[item_index]:
            if bid.account.char_id == main_id:
                return bid
        return None

    def announce(self):
        if len(self.items) > 1:
            bid_link = self.get_auction_list()
            bid_link = self.text.paginate_single(ChatBlob("Click to bid", bid_link.msg), self.conn)
            msg = "\n<yellow>----------------------------------------</yellow>\n"
            msg += "<yellow>%s</yellow> has started an auction for <yellow>%d</yellow> items.\n" % (self.auctioneer.name, len(self.items))
            msg += "%s\n" % bid_link
            msg += "<yellow>----------------------------------------</yellow>"
        else:
            item_index = list(self.items.keys())[0]
            item = self.items[item_index]
            sql = "SELECT winning_bid FROM auction_log WHERE item_name LIKE ? ORDER BY created_at DESC LIMIT 5"
            bids = self.db.query(sql, [item])
            if bids:
                avg_win_bid = int(sum(map(lambda x: x.winning_bid, bids)) / len(bids))
            else:
                avg_win_bid = 0

            bid_link = self.get_auction_list()
            bid_link = self.text.paginate_single(ChatBlob("Click to bid", bid_link.msg), self.conn)
            msg = "\n<yellow>----------------------------------------</yellow>\n"
            msg += "<yellow>%s</yellow> has started an auction for <yellow>%s</yellow>.\n" % (self.auctioneer.name, item)
            msg += "Average winning bid: <highlight>%s</highlight>\n" % avg_win_bid
            msg += "%s\n" % bid_link
            msg += "<yellow>----------------------------------------</yellow>"

        self.spam_raid_message(msg)
