import re

from core.command_param_types import Const, Options, Int, Any
from core.decorators import command, instance
from core.setting_types import TimeSettingType
from .auction_strategy.auction_strategy import AuctionStrategy


@instance()
class AuctionController:
    def __init__(self):
        self.auction: AuctionStrategy = None

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.setting_service = registry.get_instance("setting_service")
        self.alts_service = registry.get_instance("alts_service")
        self.raid_controller = registry.get_instance("raid_controller")

    def start(self):
        self.setting_service.register(self.module_name, "auction_length", "90s", TimeSettingType(), "Regular auction duration")

        self.db.exec("CREATE TABLE IF NOT EXISTS auction_log (auction_id INT PRIMARY KEY AUTO_INCREMENT, item_ref VARCHAR(255) NOT NULL, item_name VARCHAR(255) NOT NULL, "
                     "winner_id BIGINT NOT NULL, auctioneer_id BIGINT NOT NULL, created_at INT NOT NULL, winning_bid INT NOT NULL)")

    @command(command="auction", params=[], description="Show auction status",
             access_level="member")
    def auction_cmd(self, request):
        if not self.is_auction_running():
            return "No auction running."

        return self.auction.get_auction_list()

    @command(command="auction", params=[Options(["cancel"])], description="Cancel ongoing auction",
             access_level="moderator", sub_command="modify")
    def auction_cancel_cmd(self, request, _):
        if not self.is_auction_running():
            return "No auction running."

        result = self.auction.cancel(request.sender)
        self.auction = None
        return result

    @command(command="auction", params=[Const("bid"), Int("amount"), Int("item_index", is_optional=True)],
             description="Bid on an item", access_level="member")
    def auction_bid_cmd(self, request, _, amount, item_index):
        if not self.is_auction_running():
            return "No auction running."

        if not self.is_in_raid(request.sender.char_id):
            return "You must be in the raid in order to bid on an item."

        return self.auction.add_bid(request.sender, amount, item_index)

    @command(command="auction", params=[Const("bid"), Const("all"), Int("item_index", is_optional=True)],
             description="Bid on an item", access_level="member")
    def auction_bid_all_cmd(self, request, _1, _2, item_index):
        if not self.is_auction_running():
            return "No auction running."

        if not self.is_in_raid(request.sender.char_id):
            return "You must be in the raid in order to bid on an item."

        return self.auction.add_bid(request.sender, "all", item_index)

    @command(command="auction", params=[Const("unbid"), Int("item_index", is_optional=True)],
             description="Remove a bid from an item", access_level="member")
    def auction_unbid_cmd(self, request, _, item_index):
        if not self.is_auction_running():
            return "No auction running."

        return self.auction.remove_bid(request.sender, item_index)

    @command(command="auction", params=[Const("end")], description="End an auction, and display the winners",
             access_level="moderator", sub_command="modify")
    def auction_end_cmd(self, request, _):
        if not self.is_auction_running():
            return "Auction is not running."

        self.auction.end()

    @command(command="auction", params=[Const("announce")], description="Announce the auction",
             access_level="moderator", sub_command="modify")
    def auction_announce_cmd(self, request, _):
        if not self.is_auction_running():
            return "Auction is not running."

        self.auction.announce()

    @command(command="auction", params=[Const("start", is_optional=True), Any("items")], description="Start an auction, with one or more items",
             access_level="moderator", sub_command="modify")
    def auction_start_cmd(self, request, _, items):
        if self.is_auction_running():
            return "Auction already running."

        items = re.findall(r"(([^<]+)?<a href=[\"\']itemref://(\d+)/(\d+)/(\d+)[\"\']>([^<]+)</a>([^<]+)?)", items)
        self.auction = AuctionStrategy(request.conn)
        for item in items:
            self.auction.add_item(item[0])

        auction_length = self.setting_service.get("auction_length").get_value()

        # TODO create timer
        return self.auction.start(request.sender, auction_length)

    def is_in_raid(self, char_id):
        main_id = self.alts_service.get_main(char_id).char_id
        return self.raid_controller.raid is None or self.raid_controller.is_in_raid(main_id)

    def is_auction_running(self):
        return self.auction and self.auction.is_running
