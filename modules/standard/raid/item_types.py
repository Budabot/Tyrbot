class AOItem:
    def __init__(self, low_id, high_id, ql, name, icon_id=None):
        self.low_id = low_id
        self.high_id = high_id
        self.ql = ql
        self.name = name
        self.icon_id = icon_id


class LootItem:
    def __init__(self, item, prefix=None, suffix=None, count=1):
        item = AOItem(item["low_id"], item["high_id"], item["ql"], item["name"])
        self.item: AOItem = item
        self.bidders = []
        self.count = count
        self.prefix = prefix
        self.suffix = suffix


class AuctionItem(LootItem):
    def __init__(self, item, auctioneer_id, prefix=None, suffix=None, count=1):
        super().__init__(item, prefix, suffix, count)
        self.auctioneer_id = auctioneer_id
        self.winner_id = None
        self.winning_bid = 0
        self.second_highest = 0
