import unittest

from core.text import Text
from modules.standard.guide.aou_controller import AOUController


class AOUControllerTest(unittest.TestCase):
    # test format with: !aou 45,
    # ao-universe bbcode reference: https://www.ao-universe.com/mobile/parser.php#bbcode

    def test_format_bbcode_code(self):
        aou_controller = AOUController()
        aou_controller.text = Text()

        self.assertEqual("<i><highlight>test<end></i>", aou_controller.format_bbcode_code("[center][i][b]test[/b][/i][/center]"))
        self.assertEqual("\n", aou_controller.format_bbcode_code("\n"))
        self.assertEqual("testtest", aou_controller.format_bbcode_code("[color=#FFCC77]test[/color][color=red]test[/color]"))
        self.assertEqual("-image--image-", aou_controller.format_bbcode_code("[center][img]something1.png[/img][img]something2.png[/img][/center]"))
        self.assertEqual("<a  href='chatcmd:///start test.com'>testing</a>", aou_controller.format_bbcode_code("[url=test.com]testing[/url]"))
        self.assertEqual("<a  href='chatcmd:///tell <myname> aou 10'>testing</a>", aou_controller.format_bbcode_code("[url=index.php?pid=10]testing[/url]"))
        self.assertEqual("<a  href='chatcmd:///waypoint 456 254 100'>Cool spot (456x254)</a>", aou_controller.format_bbcode_code("[waypoint pf=100 y=254 x=456]Cool spot[/waypoint]"))
