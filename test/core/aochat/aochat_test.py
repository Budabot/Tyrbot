import unittest

from core.aochat.extended_message import ExtendedMessage
from core.aochat.mmdb_parser import MMDBParser
from core.aochat.server_packets import SystemMessage, PublicChannelMessage


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

    def test_public_channel_message(self):
        # tests PublicChannelMessage with an ExtendedMessage containing a tower victory
        mmdb_parser = MMDBParser("../../../text.mdb")

        packet = PublicChannelMessage.from_bytes(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x53~&!!!&r!5b/RR!!!8S!!!!#s\x09TestOrg1s\x09TestCharR!!!8S!!!!"s\x09TestOrg2s\x05Morti!!!Dui!!!Eu~\x00\x04Test')

        msg = packet.message[2:-1]
        category_id = mmdb_parser.read_base_85(msg[0:5].encode("utf-8"))
        instance_id = mmdb_parser.read_base_85(msg[5: 10].encode("utf-8"))
        template = mmdb_parser.get_message_string(category_id, instance_id)
        params = mmdb_parser.parse_params(msg[10:].encode("utf-8"))
        extended_message = ExtendedMessage(category_id, instance_id, template, params)

        self.assertEqual("The omni organization TestOrg1 just entered a state of war! TestChar attacked the clan organization TestOrg2's tower in Mort at location (3059,3144).", extended_message.get_message())
