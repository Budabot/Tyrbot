import re
import unittest

from core.command_param_types import Const, Int, Decimal, Any, Options, Time, Item, NamedParameters


class CommandParamTypesTest(unittest.TestCase):
    def test_const(self):
        param = Const("test")
        self.assertEqual("test", self.param_test(param, "test"))
        self.assertIsNone(self.param_test(param, "not_test"))
        self.assertIsNone(self.param_test(param, "test_not"))

    def test_int(self):
        param = Int("hello")
        self.assertEqual(10, self.param_test(param, "10"))
        self.assertIsNone(self.param_test(param, "ten"))

    def test_decimal(self):
        param = Decimal("test")
        self.assertEqual(10, self.param_test(param, "10"))
        self.assertEqual(10, self.param_test(param, "10.0"))
        self.assertEqual(10.1, self.param_test(param, "10.1"))
        self.assertIsNone(self.param_test(param, "ten"))

    def test_any(self):
        param = Any("test")
        self.assertEqual("10", self.param_test(param, "10"))
        self.assertEqual("ten", self.param_test(param, "ten"))
        self.assertEqual("?this is a test.", self.param_test(param, "?this is a test."))
        self.assertIsNone(self.param_test(param, ""))

    def test_options(self):
        param = Options(["test1", "test2", "test3"])
        self.assertEqual("test1", self.param_test(param, "test1"))
        self.assertEqual("test2", self.param_test(param, "test2"))
        self.assertEqual("test3", self.param_test(param, "test3"))
        self.assertIsNone(self.param_test(param, "test4"))

    def test_time(self):
        param = Time("test")
        # needed to resolve dependency to Util...not sure how this is working
        from core.util import Util
        self.assertEqual(600, self.param_test(param, "10m"))
        self.assertIsNone(self.param_test(param, "test"))

    def test_item(self):
        param = Item("test")
        self.assertEqual({'high_id': 2, 'low_id': 1, 'name': 'test', 'ql': 3}, self.param_test(param, "<a href=\"itemref://1/2/3\">test</a>"))
        self.assertIsNone(self.param_test(param, "test"))

    def test_character(self):
        pass

    def test_named_parameters(self):
        param = NamedParameters(["test1", "test2", "test3"])
        self.assertEqual({'test1': '1', 'test2': '2', 'test3': '3'}, self.param_test(param, "--test1=1 --test2=2 --test3=3"))
        self.assertEqual({'test1': '1', 'test2': '2', 'test3': '3'}, self.param_test(param, "--test3=3 --test2=2 --test1=1"))
        self.assertEqual({'test1': '', 'test2': '2', 'test3': ''}, self.param_test(param, "--test2=2"))
        self.assertIsNone(self.param_test(param, ""))

    def param_test(self, param, param_input):
        regex = param.get_regex()
        matches = re.search("^" + regex + "$", " " + param_input)
        if matches:
            return param.process_matches(list(matches.groups()))
        else:
            return None
