import unittest

from core.aochat.extended_message import ExtendedMessage
from core.aochat.mmdb_parser import MMDBParser
from core.aochat.server_packets import SystemMessage


class AOChatTest(unittest.TestCase):

    def test_system_message(self):
        # tests SystemMessage with an ExtendedMessage containing a reference param
        mmdb_parser = MMDBParser("../../../text.mdb")

        packet = SystemMessage.from_bytes(b'\x00\x05\xc0\xbe\x00\x00\x00\x00\x03@\xe2E\x00\x05l\x0f\xcf\xcaw')

        category_id = 20000
        instance_id = packet.message_id
        template = mmdb_parser.get_message_string(category_id, instance_id)
        params = mmdb_parser.parse_params(packet.message_args)
        extended_message = ExtendedMessage(category_id, instance_id, template, params)

        self.assertEqual("Could not send message to offline player: the message is too big to fit in the inbox", extended_message.get_message())
