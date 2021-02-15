from core.chat_blob import ChatBlob
from core.text import Text, TextFormatter
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
        setting.get_font_color = MagicMock(return_value="<font>")
        setting_service = Mock()
        setting_service.get = MagicMock(return_value=setting)

        public_channel_service = Mock()
        public_channel_service.get_org_name = MagicMock(return_value="org")

        text = Text()
        text.setting_service = setting_service
        text.public_channel_service = public_channel_service

        conn = Mock()
        conn.get_char_name = MagicMock(return_value="char_name")
        conn.get_org_name = MagicMock(return_value="org_name")

        msg = "hello this is a test\nthis is another test as well\nand a third\ntest also\nwhich is very\nshort"
        chatblob = ChatBlob("label", msg)
        page_prefix = "test_page_prefix"
        page_postfix = "test_page_postfix"
        chatblob.page_prefix = page_prefix
        chatblob.page_postfix = page_postfix
        pages = text.paginate(chatblob, conn, max_page_length=115)

        self.assertEqual(2, len(pages))
        self.assertTrue("text://short" in pages[1])

        # page prefix
        self.assertTrue(pages[0].startswith(page_prefix))
        self.assertTrue(pages[1].startswith(page_prefix))

        # page postfix
        self.assertTrue(pages[0].endswith(page_postfix))
        self.assertTrue(pages[1].endswith(page_postfix))

        # no max_page_length
        pages2 = text.paginate(chatblob, conn)
        self.assertEqual(1, len(pages2))

    def test_get_formatted_faction(self):
        text = Text()
        self.assertEqual("<omni>Omni</omni>", text.get_formatted_faction("omni"))
        self.assertEqual("<clan>Clan</clan>", text.get_formatted_faction("clan"))
        self.assertEqual("<neutral>Neutral</neutral>", text.get_formatted_faction("neutral"))
        self.assertEqual("<unknown>Unknown</unknown>", text.get_formatted_faction("unknown"))

        self.assertEqual("<unknown>Test</unknown>", text.get_formatted_faction("test"))

        self.assertEqual("<omni>Test2</omni>", text.get_formatted_faction("omni", "Test2"))
        self.assertEqual("<clan>Test2</clan>", text.get_formatted_faction("clan", "Test2"))
        self.assertEqual("<neutral>Test2</neutral>", text.get_formatted_faction("neutral", "Test2"))
        self.assertEqual("<unknown>Test2</unknown>", text.get_formatted_faction("unknown", "Test2"))

    def test_text_formatter(self):
        setting = Mock()
        setting.get_value = MagicMock(return_value="test")
        setting.get_font_color = MagicMock(return_value="<font>")
        setting_service = Mock()
        setting_service.get = MagicMock(return_value=setting)

        bot = Mock()
        bot.get_char_name = MagicMock(return_value="char_name")
        bot.org_name = "org_name"

        conn = Mock()
        conn.get_char_name = MagicMock(return_value="char_name")
        conn.get_org_name = MagicMock(return_value="org_name")

        public_channel_service = Mock()
        public_channel_service.get_org_name = MagicMock(return_value="org")

        text = Text()
        text.setting_service = setting_service
        text.text_formatter = TextFormatter(setting_service, conn)

        messages = ["<br>", "<red>", "<blue>", "<red><symbol>Hi</red>", text.make_chatcmd("Test", "/tell <myname> test")]
        #messages = ["<red>Hi</red>", ]
        for message in messages:
            self.text_formatter_tester(text, message, conn)

    def text_formatter_tester(self, text, message, conn):
        output1 = text.format_message_old(message, conn)
        output2 = text.format_message_new(message, conn)
        #print("'" + output1 + "'")
        #print("'" + output2 + "'")
        #self.assertEqual(output1, output2)
