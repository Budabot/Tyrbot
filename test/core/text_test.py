from core.chat_blob import ChatBlob
from core.text import Text
import unittest
from unittest.mock import Mock, MagicMock


class TextTest(unittest.TestCase):

    def test_get_next_line(self):
        msg = "hello this is a test\nthis is another test as well\nand a third\ntest also\nwhich is\nshort"
        text = Text()

        self.assertEqual('hello this is a test\n', text.get_next_line(msg, {"symbol": "\n", "include": True})[0])
        self.assertEqual('hello', text.get_next_line(msg, {"symbol": " ", "include": False})[0])

    def test_paginate(self):
        setting = Mock()
        setting.get_value = MagicMock(return_value="test")
        setting.get_font_color = MagicMock(return_value="color")
        setting_service = Mock()
        setting_service.get = MagicMock(return_value=setting)

        bot = Mock()
        bot.char_name = "char_name"
        bot.org_name = "org_name"

        public_channel_service = Mock()
        public_channel_service.get_org_name = MagicMock(return_value="org")

        text = Text()
        text.setting_service = setting_service
        text.bot = bot
        text.public_channel_service = public_channel_service

        msg = "hello this is a test\nthis is another test as well\nand a third\ntest also\nwhich is very\nshort"
        chatblob = ChatBlob("label", msg)
        prefix = "test_prefix"
        postfix = "test_postfix"
        chatblob.page_prefix = prefix
        chatblob.page_postfix = postfix
        pages = text.paginate(chatblob, 110)

        self.assertEqual(2, len(pages))
        self.assertTrue("text://short" in pages[1])

        # page prefix
        self.assertTrue(pages[0].startswith(prefix))
        self.assertTrue(pages[1].startswith(prefix))

        # page postfix
        self.assertTrue(pages[0].endswith(postfix))
        self.assertTrue(pages[1].endswith(postfix))
