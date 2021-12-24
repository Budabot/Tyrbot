from core.dict_object import DictObject
from core.registry import Registry


class LootItem:
    def __init__(self, item, comment, count=1):
        self.item = item
        self.comment = comment
        self.bidders = []
        self.count = count

    def get_item_str(self):
        if isinstance(self.item, DictObject):
            item_name = "%s (%s)" % (self.item.name, self.comment) if self.comment else self.item.name
            text = Registry.get_instance("text")
            return text.make_item(self.item.low_id, self.item.high_id, self.item.ql, item_name)
        else:
            item_name = "<highlight>%s</highlight>" % self.item
            if self.comment:
                item_name += " (%s)" % self.comment
            return item_name

    def get_item_image(self):
        if isinstance(self.item, DictObject):
            text = Registry.get_instance("text")
            return text.make_item(self.item.low_id, self.item.high_id, self.item.ql, text.make_image(self.item.icon))
        else:
            return None

    def __str__(self):
        return "%s %d" % (self.get_item_str(), self.count)


class AuctionItem(LootItem):
    def __init__(self, item, comment, auctioneer_id, count=1):
        super().__init__(item, comment, count)
        self.auctioneer_id = auctioneer_id
        self.winner_id = None
        self.winning_bid = 0
        self.second_highest = 0
