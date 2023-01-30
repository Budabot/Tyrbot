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
    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.text: Text = registry.get_instance("text")
        self.util: Util = registry.get_instance("util")
        self.setting_service = registry.get_instance("setting_service")
        self.items_controller = registry.get_instance("items_controller")

    def start(self):
        self.setting_service.register(self.module_name, "gmi_api_url", "https://gmi.us.nadybot.org/v1.0/aoid/{item_id}",
                                      TextSettingType(["https://gmi.us.nadybot.org/v1.0/aoid/{item_id}", "https://gmi.eu.nadybot.org/v1.0/aoid/{item_id}"]),
                                      "URL for the GMI API")

    @command(command="gmi", params=[Int("item_id")], access_level="guest",
             description="Search for GMI listings by item id",
             extended_description="Use <symbol>items to search for an item by name")
    def gmi_id_cmd(self, request, item_id):
        url = self.setting_service.get("gmi_api_url").get_value().format(item_id=item_id)
        r = requests.get(url, headers={"User-Agent": f"Tyrbot {self.bot.version}"}, timeout=5)
        if r.status_code == 404:
            return f"Item with id <highlight>{item_id}</highlight> does not exist on GMI."
        elif r.status_code != 200:
            return f"Error retrieving GMI listings for item id <highlight>{item_id}</highlight>."

        result = DictObject(r.json())

        item = self.items_controller.get_by_item_id(item_id)

        blob = ""
        blob += self.text.format_item(item, with_icon=True)
        blob += "\n"

        blob += "\n<header2>Buy Orders</header2>\n"
        for buy_order in result.buy_orders:
            ql = buy_order.max_ql if buy_order.max_ql == buy_order.min_ql else "%s - %s" % (buy_order.min_ql, buy_order.max_ql)
            blob += "%s [QL%s] x%d %s expires in %s\n" % (
                self.util.format_number(buy_order.price),
                ql,
                buy_order.count,
                self.text.make_chatcmd(buy_order.buyer, "/tell %s" % buy_order.buyer),
                self.util.time_to_readable(buy_order.expiration))

        blob += "\n<header2>Sell Orders</header2>\n"
        for sell_order in result.sell_orders:
            blob += "%s [QL%s] x%d %s expires in %s\n" % (
                self.util.format_number(sell_order.price),
                sell_order.ql,
                sell_order.count,
                self.text.make_chatcmd(sell_order.seller, "/tell %s" % sell_order.seller),
                self.util.time_to_readable(sell_order.expiration))

        blob += "\nGMI Results provided by <highlight>The Nadybot Team</highlight>"

        if len(result.buy_orders) + len(result.sell_orders) == 0:
            blob = ""

        return ChatBlob("GMI Results (%d Buy Orders, %s Sell Orders)" % (len(result.buy_orders), len(result.sell_orders)), blob)
