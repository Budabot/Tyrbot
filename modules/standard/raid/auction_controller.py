import re

from core.command_param_types import Const, Options, Int, Any
from core.decorators import command, instance, setting
from core.setting_types import TimeSettingType
from .auction_strategy.auction_strategy import AuctionStrategy


@instance()
class AuctionController:
    def __init__(self):
        self.auction: AuctionStrategy = None

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.setting_service = registry.get_instance("setting_service")

    def start(self):
        self.setting_service.register_new(self.module_name, "auction_length", "90s", TimeSettingType(), "Regular auction duration")
        self.setting_service.register_new(self.module_name, "auction_announce_interval", "15s", TimeSettingType(), "Auction announce interval")

        self.db.exec("CREATE TABLE IF NOT EXISTS auction_log (auction_id INT PRIMARY KEY AUTO_INCREMENT, item_ref VARCHAR(255) NOT NULL, item_name VARCHAR(255) NOT NULL, "
                     "winner_id BIGINT NOT NULL, auctioneer_id BIGINT NOT NULL, created_at INT NOT NULL, winning_bid INT NOT NULL)")

    @command(command="auction", params=[], description="Show auction status",
             access_level="member")
    def auction_cmd(self, request):
        if not self.is_auction_running():
            return "No auction running."

        return self.auction.get_auction_list()

    @command(command="auction", params=[Options(["cancel", "end"])], description="Cancel ongoing auction",
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

        return self.auction.add_bid(request.sender, amount, item_index)

    @command(command="auction", params=[Const("bid"), Const("all"), Int("item_index", is_optional=True)],
             description="Bid on an item", access_level="member")
    def auction_bid_all_cmd(self, request, _1, _2, item_index):
        if not self.is_auction_running():
            return "No auction running."

        return self.auction.add_bid(request.sender, "all", item_index)

    @command(command="auction", params=[Const("start", is_optional=True), Any("items")], description="Start an auction, with one or more items",
             access_level="moderator", sub_command="modify")
    def auction_start_cmd(self, request, _, items):
        if self.is_auction_running():
            return "Auction already running."

        items = re.findall(r"(([^<]+)?<a href=[\"\']itemref://(\d+)/(\d+)/(\d+)[\"\']>([^<]+)</a>([^<]+)?)", items)
        # TODO choose auction strategy impl
        self.auction = AuctionStrategy()
        for item in items:
            self.auction.add_item(item[0])

        auction_length = self.setting_service.get("auction_length").get_value()
        announce_interval = self.setting_service.get("auction_announce_interval").get_value()

        return self.auction.start(request.sender, auction_length, announce_interval)

    def is_auction_running(self):
        return self.auction and self.auction.is_running
