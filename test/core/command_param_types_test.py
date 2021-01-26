import re
import unittest

from core.command_param_types import Const, Int, Decimal, Any, Options, Time, Item, NamedParameters, \
    NamedFlagParameters, Multiple, Regex
from core.registry import Registry # required
from core.util import Util # required


class CommandParamTypesTest(unittest.TestCase):
    def test_const(self):
        param = Const("test")
        self.assertEqual("test", self.param_test_helper(param, "test"))
        self.assertIsNone(self.param_test_helper(param, "not_test"))
        self.assertIsNone(self.param_test_helper(param, "test_not"))

    def test_int(self):
        param = Int("hello")
        self.assertEqual(10, self.param_test_helper(param, "10"))
        self.assertIsNone(self.param_test_helper(param, "ten"))

    def test_decimal(self):
        param = Decimal("test")
        self.assertEqual(10, self.param_test_helper(param, "10"))
        self.assertEqual(10, self.param_test_helper(param, "10.0"))
        self.assertEqual(10.1, self.param_test_helper(param, "10.1"))
        self.assertIsNone(self.param_test_helper(param, "ten"))

    def test_any(self):
        param = Any("test")
        self.assertEqual("10", self.param_test_helper(param, "10"))
        self.assertEqual("ten", self.param_test_helper(param, "ten"))
        self.assertEqual("?this is a test.", self.param_test_helper(param, "?this is a test."))
        self.assertIsNone(self.param_test_helper(param, ""))

    def test_options(self):
        param = Options(["test1", "test2", "test3"])
        self.assertEqual("test1", self.param_test_helper(param, "test1"))
        self.assertEqual("test2", self.param_test_helper(param, "test2"))
        self.assertEqual("test3", self.param_test_helper(param, "test3"))
        self.assertIsNone(self.param_test_helper(param, "test4"))

    def test_time(self):
        param = Time("test")
        # needed to resolve dependency to Util...not sure how this is working
        from core.util import Util
        self.assertEqual(600, self.param_test_helper(param, "10m"))
        self.assertEqual(304, self.param_test_helper(param, "5M4S"))
        self.assertIsNone(self.param_test_helper(param, "test"))

    def test_item(self):
        param = Item("test")
        self.assertEqual({'high_id': 2, 'low_id': 1, 'name': 'test', 'ql': 3},
                         self.param_test_helper(param, "<a href=\"itemref://1/2/3\">test</a>"))
        self.assertEqual({'high_id': 101, 'low_id': 100, 'name': 'It\'s working!', 'ql': 300},
                         self.param_test_helper(param, "<a href=\"itemref://100/101/300\">It's working!</a>"))
        self.assertIsNone(self.param_test_helper(param, "test"))

    def test_character(self):
        pass

    def test_named_parameters(self):
        param = NamedParameters(["test1", "test2", "test3"])
        self.assertEqual({'test1': '1', 'test2': '2', 'test3': '3'}, self.param_test_helper(param, "--test1=1 --test2=2 --test3=3"))
        self.assertEqual({'test1': '1', 'test2': '2', 'test3': '3'}, self.param_test_helper(param, "--test3=3 --test2=2 --test1=1"))
        self.assertEqual({'test1': '', 'test2': '2', 'test3': ''}, self.param_test_helper(param, "--test2=2"))
        self.assertEqual({'test1': 'one and two and three', 'test2': '', 'test3': ''}, self.param_test_helper(param, "--test1=one and two and three"))
        self.assertEqual({'test1': 'one and two', 'test2': '', 'test3': 'three and four'}, self.param_test_helper(param, "--test1=one and two --test3=three and four"))
        self.assertIsNone(self.param_test_helper(param, ""))

    def test_named_flag_parameters(self):
        param = NamedFlagParameters(["test1", "test2", "test3"])
        self.assertEqual({'test1': True, 'test2': True, 'test3': True}, self.param_test_helper(param, "--test1 --test2 --test3"))
        self.assertEqual({'test1': True, 'test2': True, 'test3': True}, self.param_test_helper(param, "--test3 --test2 --test1"))
        self.assertEqual({'test1': False, 'test2': True, 'test3': False}, self.param_test_helper(param, "--test2"))
        self.assertEqual({'test1': False, 'test2': True, 'test3': True}, self.param_test_helper(param, "--test2 --test3"))
        self.assertEqual({'test1': True, 'test2': True, 'test3': False}, self.param_test_helper(param, "--test2 --test1"))
        self.assertIsNone(self.param_test_helper(param, ""))

    def test_multiple(self):
        param1 = Multiple(Int("num"))
        self.assertEqual([1], self.param_test_helper(param1, "1"))
        self.assertEqual([1, 2, 3], self.param_test_helper(param1, "1 2 3"))

        param2 = Multiple(Const("something"))
        self.assertEqual(["something"], self.param_test_helper(param2, "something"))
        self.assertEqual(["something", "something", "something"],
                         self.param_test_helper(param2, "something something something"))

        param3 = Multiple(Time("time"))
        self.assertEqual([60], self.param_test_helper(param3, "1m"))
        self.assertEqual([304], self.param_test_helper(param3, "5M4S"))
        self.assertEqual([60, 304, 14521], self.param_test_helper(param3, "1m 5M4S 4h2m1s"))

        param4 = Multiple(Item("item"))
        self.assertEqual([{'low_id': 246817, 'high_id': 246817, 'ql': 200, 'name': 'Novictum Seed'}],
                         self.param_test_helper(param4, "<a href=\"itemref://246817/246817/200\">Novictum Seed</a>"))

        self.assertEqual([{'low_id': 246817, 'high_id': 246817, 'ql': 200, 'name': 'Novictum Seed'},
                          {'low_id': 100, 'high_id': 101, 'ql': 300, 'name': 'It\'s cool'}],
                         self.param_test_helper(param4, "<a href=\"itemref://246817/246817/200\">Novictum Seed</a> "
                                                        "<a href=\"itemref://100/101/300\">It's cool</a>"))

        self.assertEqual([{'low_id': 246817, 'high_id': 246817, 'ql': 200, 'name': 'Novictum Seed'},
                          {'low_id': 100, 'high_id': 101, 'ql': 300, 'name': 'It\'s cool'},
                          {'low_id': 12345, 'high_id': 54321, 'ql': 123, 'name': 'It Works!'}],
                         self.param_test_helper(param4,
                                                "<a href=\"itemref://246817/246817/200\">Novictum Seed</a> "
                                                "<a href=\"itemref://100/101/300\">It's cool</a> "
                                                "<a href=\"itemref://12345/54321/123\">It Works!</a>"))

        param5 = Multiple(Any("time"))
        self.assertEqual(["test"], self.param_test_helper(param5, "test"))
        self.assertEqual(["test1", "test2"], self.param_test_helper(param5, "test1 test2"))
        self.assertEqual(["test1", "test2", "test3"], self.param_test_helper(param5, "test1 test2 test3"))

    def param_test_helper(self, param, param_input):
        regex = param.get_regex()
        matches = re.search("^" + regex + "$", " " + param_input, re.IGNORECASE | re.DOTALL)
        if matches:
            return param.process_matches(list(matches.groups()))
        else:
            return None
