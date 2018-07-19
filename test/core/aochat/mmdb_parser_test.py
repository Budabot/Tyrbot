import unittest

from core.aochat.mmdb_parser import MMDBParser


class MMDBParserTest(unittest.TestCase):

    def test_parse_params1(self):
        mmdb_parser = MMDBParser("../../../text.mdb")

        params = mmdb_parser.parse_params(b'R!!!8S!!!!#s\x09TestOrg1s\x09TestCharR!!!8S!!!!"s\x09TestOrg2s\x05Testi!!!Dui!!!Eu')

        self.assertEqual(['omni', 'TestOrg1', 'TestChar', 'clan', 'TestOrg2', 'Test', 3059, 3144], params)

    def test_parse_params2(self):
        mmdb_parser = MMDBParser("../../../text.mdb")

        params = mmdb_parser.parse_params(b'l\x0f\xcf\xcaw')

        self.assertEqual(['the message is too big to fit in the inbox'], params)
