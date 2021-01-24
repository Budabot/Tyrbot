import unittest
from core.util import Util


class UtilTest(unittest.TestCase):

    def test_time_to_readable(self):
        util = Util()
        self.assertEqual('0 secs', util.time_to_readable(0))
        self.assertEqual('1 sec', util.time_to_readable(1))
        self.assertEqual('59 secs', util.time_to_readable(59))
        self.assertEqual('1 min', util.time_to_readable(60))
        self.assertEqual('1 min 1 sec', util.time_to_readable(61))
        self.assertEqual('1 hr', util.time_to_readable(3600))
        self.assertEqual('7 days', util.time_to_readable(604800))
        self.assertEqual('1 week', util.time_to_readable(604800, max_unit="week"))
        self.assertEqual('168 hrs', util.time_to_readable(604800, max_unit="hr"))
        self.assertEqual('1 day', util.time_to_readable(86410))
        self.assertEqual('1 day 10 secs', util.time_to_readable(86410, max_levels=4))
        self.assertEqual('1 min 12 secs', util.time_to_readable(72))

    def test_parse_time(self):
        util = Util()
        self.assertEqual(10, util.parse_time("10S"))
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

    def test_format_date(self):
        util = Util()
        self.assertEqual("2009-02-14", util.format_date(1234597890))
        self.assertEqual("2018-08-10", util.format_date(1533873922))

    def test_format_datetime(self):
        util = Util()
        self.assertEqual("2009-02-14 07:51:30 UTC", util.format_datetime(1234597890))
        self.assertEqual("2018-08-10 04:05:22 UTC", util.format_datetime(1533873922))

    def test_interpolate_value(self):
        util = Util()

        # empty interpolation_ranges
        self.assertEqual(None, util.interpolate_value(1, {}))

        # ql outside of single interpolation_ranges
        self.assertEqual(None, util.interpolate_value(2, {1: 1}))

        # ql on interpolation_range lower boundary
        self.assertEqual(1, util.interpolate_value(1, {1: 1, 100: 100}))

        # ql on interpolation_range upper boundary
        self.assertEqual(100, util.interpolate_value(100, {1: 1, 100: 100}))

        # ql outside of multiple interpolation_ranges
        self.assertEqual(None, util.interpolate_value(101, {1: 1, 100: 100}))

        # ql within interpolation_range
        self.assertEqual(50, util.interpolate_value(50, {1: 1, 100: 100}))
        self.assertEqual(50, util.interpolate_value(50, {1: 1, 100: 100, 101: 101, 200: 400}))
        self.assertEqual(653, util.interpolate_value(137, {1: 11, 200: 951}))
        self.assertEqual(249, util.interpolate_value(150, {1: 1, 100: 100, 101: 101, 200: 400}))
        self.assertEqual(55, util.interpolate_value(200, {1: 5, 200: 55, 201: 55, 300: 73}))

        # test reverse order
        self.assertEqual(55, util.interpolate_value(200, {300: 73, 201: 55, 200: 55, 1: 5}))

        # test out of order
        self.assertEqual(55, util.interpolate_value(200, {201: 55, 300: 73, 1: 5, 200: 55}))
