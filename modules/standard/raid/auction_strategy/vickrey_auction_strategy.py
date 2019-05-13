from modules.standard.raid.auction_strategy.auction_strategy import AuctionStrategy


# class VickreyAuctionStrategy(AuctionStrategy):
#     def add_bid(self, sender: SenderObj, bid_amount, item_index):
#         if bidder.bid == amount and not new_bidder:
#             return "The submitted bid matches your current bid. You can only submit a " \
#                    "new bid if it's of higher value than the previous bid. This bid did not " \
#                    "count against your bid count for this item."
#         if bidder.bid > amount:
#             return "The submitted bid is lower than your current bid. You can only submit a " \
#                    "new bid if it's of higher value than the previous bid. This bid did not " \
#                    "count against your bid count for this item."
#
#         bidder.bid_count += 1
#         bidder.bid = amount
#         bidder_account.points_used = used + amount
#         auction_item.second_highest = auction_item.winning_bid \
#             if auction_item.winning_bid > 0 else minimum_bid
#         auction_item.winning_bid = amount
#         auction_item.winner_id = bidder.char_id
#         if new_bidder:
#             auction_item.bidders.append(bidder)
#
#         bid_count_text = "first" if bidder.bid_count == 1 else "second"
#         return "Your bid of %d points was accepted. This was your %s bid on " \
#                "this item. You have %d points left to use in the ongoing " \
#                "auction." % (amount, bid_count_text, (points_available - amount))
#
#     def get_item_info(self, item_index):
#         blob += "<header2>This is a Vickrey auction<end>\n"
#         blob += " - In a Vickrey auction, you only get to bid twice on the same item.\n"
#         blob += " - You won't be notified of the outcome of your bid, as all bids will be anonymous.\n"
#         blob += " - The highest anonymous bid will win, and pay the second-highest bid.\n"
#         blob += " - Bids are anonymous; sharing your bid with others defeat the purpose of the Vickrey format.\n"
#         blob += " - Bidding is done the same way as regular bids, as described above."
#
#     def find_vickrey_winner(self, item: AuctionItem):
#         was_rolled = False
#
#         if item.bidders:
#             minimum_bid = self.setting_service.get("minimum_bid").get_value()
#             vickrey_list = []
#             winning_bid = 0
#             winner = None
#
#             for bidder in item.bidders:
#                 if bidder.bid > winning_bid:
#                     item.second_highest = winning_bid
#                     winning_bid = bidder.bid
#                     winner = bidder.char_id
#                     vickrey_list.clear()
#                 elif bidder.bid == winning_bid and winner:
#                     # Potential pitfall if winner for some strange reason is None.
#                     # It should not be possible to do a bid of 0 or less, so we just
#                     # assume that if bid is equal to winning bid, winning bid must be
#                     # greater than 0, and thus a winner must exist from a previous
#                     # iterated bid
#                     vickrey_list.append(bidder.char_id)
#
#             if vickrey_list:
#                 vickrey_list.append(winner)
#                 item.second_highest = winning_bid
#                 winner = secrets.choice(vickrey_list)
#                 was_rolled = True
#
#             if winning_bid > 0 and winner:
#                 item.winning_bid = winning_bid
#                 item.winner_id = winner
#                 if item.second_highest == 0:
#                     item.second_highest = minimum_bid
#
#         return was_rolled
