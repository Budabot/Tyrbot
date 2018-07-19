import unittest

from core.aochat.mmdb_parser import MMDBParser


class MMDBParserTest(unittest.TestCase):
    def test_parse_params(self):
        # param type S
        mmdb_parser = MMDBParser("../../../text.mdb")
        params = mmdb_parser.parse_params(b'S\x00\x08TestOrg1')
        self.assertEqual(["TestOrg1"], params)

        # param type s
        mmdb_parser = MMDBParser("../../../text.mdb")
        params = mmdb_parser.parse_params(b's\x09TestOrg1')
        self.assertEqual(["TestOrg1"], params)

        # param type I
        mmdb_parser = MMDBParser("../../../text.mdb")
        params = mmdb_parser.parse_params(b'I\x01\x02\x03\x04')
        self.assertEqual([16909060], params)

        # param type i, u
        params = mmdb_parser.parse_params(b'i\x21\x21\x21\x21\x31')
        self.assertEqual([16], params)

        # param type R
        params = mmdb_parser.parse_params(b'R!!!8S!!!!#')
        self.assertEqual(["omni"], params)

        # param type l
        params = mmdb_parser.parse_params(b'l\x0f\xcf\xcaw')
        self.assertEqual(["the message is too big to fit in the inbox"], params)

        # multiple
        params = mmdb_parser.parse_params(b'R!!!8S!!!!#s\x09TestOrg1s\x09TestCharR!!!8S!!!!"s\x09TestOrg2s\x05Testi!!!Dui!!!Eu')
        self.assertEqual(['omni', 'TestOrg1', 'TestChar', 'clan', 'TestOrg2', 'Test', 3059, 3144], params)
