from core.text import Text
import unittest
from unittest.mock import Mock, MagicMock


class TextTest(unittest.TestCase):

    def test_get_next_line(self):
        msg = "hello this is a test\nthis is another test as well\nand a third\ntest also\nwhich is\nshort"
        text = Text()

        self.assertEqual(text.get_next_line(msg, {"symbol": "\n", "include": True})[0], 'hello this is a test\n')
        self.assertEqual(text.get_next_line(msg, {"symbol": " ", "include": False})[0], 'hello')

    def test_paginate(self):
        setting = Mock()
        setting.get_value = MagicMock(return_value="test")
        setting_manager = Mock()
        setting_manager.get = MagicMock(return_value=setting)

        bot = Mock()
        bot.char_name = "char_name"
        bot.org_name = "org_name"

        text = Text()
        text.setting_manager = setting_manager
        text.bot = bot

        msg = "hello this is a test\nthis is another test as well\nand a third\ntest also\nwhich is\nshort"
        pages = text.paginate("label", msg, 115)
        self.assertEqual(len(pages), 2)
        self.assertTrue("text://short" in pages[1])
