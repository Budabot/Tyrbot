import re

from core.command_param_types import Const, Options, Int, Any
from core.decorators import command, instance, setting
from core.setting_types import TimeSettingType
from modules.standard.raid.auction_strategy.auction_strategy import AuctionStrategy


@instance()
class AuctionController:
    def __init__(self):
        self.auction: AuctionStrategy = None

    @setting(name="auction_length", value="90s", description="Regular auction length in seconds")
    def auction_length(self):
        return TimeSettingType()

    @setting(name="auction_announce_interval", value="15s", description="Auction announce interval")
    def auction_announce_interval(self):
        return TimeSettingType()

    @command(command="auction", params=[], description="Show auction status",
             access_level="member")
    def auction_cmd(self, request):
        if not self.is_auction_running():
            return "No auction running."

        return self.auction.get_auction_list()

    @command(command="auction", params=[Const("start"), Any("items")], description="Start an auction, with one or more items",
             access_level="moderator", sub_command="modify")
    def auction_start_cmd(self, request, _, items):
        if self.is_auction_running():
            return "Auction already running."

        items = re.findall(r"(([^<]+)?<a href=[\"\']itemref://(\d+)/(\d+)/(\d+)[\"\']>([^<]+)</a>([^<]+)?)", items)
        # TODO choose auction strategy impl
        self.auction = AuctionStrategy()
        for item in items:
            self.auction.add_item(item[0])

        auction_length = self.auction_length().get_value()
        announce_interval = self.auction_announce_interval().get_value()

        return self.auction.start(request.sender, auction_length, announce_interval)

    @command(command="auction", params=[Options(["cancel", "end"])], description="Cancel ongoing auction",
             access_level="moderator", sub_command="modify")
    def auction_cancel_cmd(self, request, _):
        if not self.is_auction_running():
            return "No auction running."

        result = self.auction.cancel(request.sender)
        self.auction = None
        return result

    @command(command="auction", params=[Const("bid"),
                                        Int("amount", is_optional=True),
                                        Const("all", is_optional=True),
                                        Int("item_index", is_optional=True)],
             description="Bid on an item", access_level="member")
    def auction_bid_cmd(self, request, _, amount, all_amount, item_index):
        if not self.is_auction_running():
            return "No auction running."

        return self.auction.add_bid(request.sender, all_amount or amount, item_index)

    def is_auction_running(self):
        return self.auction and self.auction.is_running
