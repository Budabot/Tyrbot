import unittest

from core.sender_obj import SenderObj


class SenderObjTest(unittest.TestCase):
    def test_str(self):
        sender = SenderObj(1, "Test", None)
        self.assertEqual(SenderObj(1, "Test", None), sender)
        self.assertEqual("{'char_id': 1, 'name': 'Test', 'access_level': None}", str(sender))
        self.assertEqual("[{'char_id': 1, 'name': 'Test', 'access_level': None}]", str([sender]))
