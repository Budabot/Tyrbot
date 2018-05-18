import unittest
from core.util import Util


class UtilTest(unittest.TestCase):

    def test_time_to_readable(self):
        util = Util()
        self.assertEqual(util.time_to_readable(0), '0 secs')
        self.assertEqual(util.time_to_readable(1), '1 sec')
        self.assertEqual(util.time_to_readable(59), '59 secs')
        self.assertEqual(util.time_to_readable(60), '1 min')
        self.assertEqual(util.time_to_readable(3600), '1 hr')
        self.assertEqual(util.time_to_readable(604800), '7 days')
        self.assertEqual(util.time_to_readable(604800, max_unit="week"), '1 week')
        self.assertEqual(util.time_to_readable(604800, max_unit="hr"), '168 hrs')
        self.assertEqual(util.time_to_readable(86410), '1 day')
        self.assertEqual(util.time_to_readable(86410, max_levels=4), '1 day 10 secs')

    def test_parse_time(self):
        util = Util()
        self.assertEqual(util.parse_time("10s"), 10)
        self.assertEqual(util.parse_time("10s sdfsd", "hola"), "hola")
        self.assertEqual(util.parse_time("1m10s"), 70)
        self.assertEqual(util.parse_time("10s1m"), 70)
        self.assertEqual(util.parse_time("10s1m"), 70)
        self.assertEqual(util.parse_time("1s3hr2d1m"), 183661)

    def test_get_ability(self):
        util = Util()
        self.assertEqual("Agility", util.get_ability("Agility"))
        self.assertEqual("Agility", util.get_ability("Agil"))
        self.assertEqual("Agility", util.get_ability("A"))
        self.assertEqual("Agility", util.get_ability("a"))
        self.assertEqual("Agility", util.get_ability("agility"))
        self.assertEqual(None, util.get_ability("agilityy"))
        self.assertEqual(None, util.get_ability("agilb"))
