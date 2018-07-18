import unittest
from core.util import Util


class UtilTest(unittest.TestCase):

    def test_time_to_readable(self):
        util = Util()
        self.assertEqual('0 secs', util.time_to_readable(0))
        self.assertEqual('1 sec', util.time_to_readable(1))
        self.assertEqual('59 secs', util.time_to_readable(59))
        self.assertEqual('1 min', util.time_to_readable(60))
        self.assertEqual('1 hr', util.time_to_readable(3600))
        self.assertEqual('7 days', util.time_to_readable(604800))
        self.assertEqual('1 week', util.time_to_readable(604800, max_unit="week"))
        self.assertEqual('168 hrs', util.time_to_readable(604800, max_unit="hr"))
        self.assertEqual('1 day', util.time_to_readable(86410))
        self.assertEqual('1 day 10 secs', util.time_to_readable(86410, max_levels=4))

    def test_parse_time(self):
        util = Util()
        self.assertEqual(10, util.parse_time("10s"))
        self.assertEqual("hola", util.parse_time("10s sdfsd", "hola"))
        self.assertEqual(70, util.parse_time("1m10s"))
        self.assertEqual(70, util.parse_time("10s1m"))
        self.assertEqual(70, util.parse_time("10s1m"))
        self.assertEqual(183661, util.parse_time("1s3hr2d1m"))

    def test_get_ability(self):
        util = Util()
        self.assertEqual("Agility", util.get_ability("Agility"))
        self.assertEqual("Agility", util.get_ability("Agil"))
        self.assertEqual("Agility", util.get_ability("A"))
        self.assertEqual("Agility", util.get_ability("a"))
        self.assertEqual("Agility", util.get_ability("agility"))
        self.assertEqual(None, util.get_ability("agilityy"))
        self.assertEqual(None, util.get_ability("agilb"))
