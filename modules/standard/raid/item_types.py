from core.dict_object import DictObject
from core.registry import Registry


class LootItem:
    def __init__(self, item, comment, prefix=None, suffix=None, count=1):
        self.item = item
        self.comment = comment
        self.bidders = []
        self.count = count

        # TODO is prefix and suffix needed/used?
        self.prefix = prefix
        self.suffix = suffix

    def get_item_str(self):
        if isinstance(self.item, DictObject):
            item_name = "%s (%s)" % (self.item.name, self.comment) if self.comment else self.item.name
            text = Registry.get_instance("text")
            return text.make_item(self.item.low_id, self.item.high_id, self.item.ql, item_name)
        else:
            item_name = "%s (%s)" % (self.item, self.comment) if self.comment else self.item
            return item_name

    def __str__(self):
        return "%s %d" % (self.get_item_str(), self.count)


class AuctionItem(LootItem):
    def __init__(self, item, comment, auctioneer_id, prefix=None, suffix=None, count=1):
        super().__init__(item, comment, prefix, suffix, count)
        self.auctioneer_id = auctioneer_id
        self.winner_id = None
        self.winning_bid = 0
        self.second_highest = 0
