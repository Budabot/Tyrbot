import requests

from core.chat_blob import ChatBlob
from core.command_param_types import Int
from core.decorators import instance, command
from core.dict_object import DictObject
from core.setting_types import TextSettingType
from core.text import Text
from core.tyrbot import Tyrbot
from core.util import Util


@instance()
class GMIController:
    PAGE_SIZE = 30

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.text: Text = registry.get_instance("text")
        self.util: Util = registry.get_instance("util")
        self.setting_service = registry.get_instance("setting_service")

    def start(self):
        self.setting_service.register(self.module_name, "gmi_api_url", "https://gmi.us.nadybot.org/v1.0",
                                      TextSettingType(["https://gmi.us.nadybot.org/v1.0", "https://gmi.eu.nadybot.org/v1.0"]),
                                      "URL for the GMI API")

    @command(command="gmi", params=[Int("item_id")], access_level="all",
             description="Search for an item by item id")
    def gmi_id_cmd(self, request, item_id):
        url = "%s/aoid/%s" % (self.setting_service.get("gmi_api_url").get_value(), item_id)
        r = requests.get(url, headers={"User-Agent": f"Tyrbot {self.bot.version}"}, timeout=5)
        result = DictObject(r.json())

        blob = "Buy Orders\n"
        for buy_order in result.buy_orders:
            ql = buy_order.max_ql if buy_order.max_ql == buy_order.min_ql else "%s-%s" % (buy_order.min_ql, buy_order.max_ql)
            blob += "%s [QL%s] Count: %d by %s expires in %s\n" % (
                self.util.format_number(buy_order.price),
                ql,
                buy_order.count,
                self.text.make_chatcmd(buy_order.buyer, "/tell %s" % buy_order.buyer),
                self.util.time_to_readable(buy_order.expiration))

        blob += "\nSell Orders\n"
        for sell_order in result.sell_orders:
            blob += "%s [QL%s] Count: %d by %s expires in %s\n" % (
                self.util.format_number(sell_order.price),
                sell_order.ql,
                sell_order.count,
                self.text.make_chatcmd(sell_order.seller, "/tell %s" % sell_order.seller),
                self.util.time_to_readable(sell_order.expiration))

        blob += "\nGMI Results provided by <highlight>The Nadybot Team</highlight>"

        return ChatBlob("GMI Results", blob)
