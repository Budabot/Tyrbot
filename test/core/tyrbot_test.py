import unittest

from core.aochat.mmdb_parser import MMDBParser
from core.aochat.server_packets import SystemMessage, PublicChannelMessage
from core.tyrbot import Tyrbot


class TyrbotTest(unittest.TestCase):

    def test_system_message_ext_msg_handling(self):
        # tests SystemMessage with an ExtendedMessage containing a reference param
        mmdb_parser = MMDBParser("../../text.mdb")
        bot = Tyrbot()
        bot.mmdb_parser = mmdb_parser

        packet = SystemMessage.from_bytes(b'\x00\x05\xc0\xbe\x00\x00\x00\x00\x03@\xe2E\x00\x05l\x0f\xcf\xcaw')
        packet = bot.system_message_ext_msg_handling(packet)

        self.assertEqual("Could not send message to offline player: the message is too big to fit in the inbox", packet.extended_message.get_message())

    def test_public_channel_message_ext_msg_handling(self):
        # tests PublicChannelMessage with an ExtendedMessage containing a tower attack
        mmdb_parser = MMDBParser("../../text.mdb")
        bot = Tyrbot()
        bot.mmdb_parser = mmdb_parser

        packet = PublicChannelMessage.from_bytes(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x53~&!!!&r!5b/RR!!!8S!!!!#s\x09TestOrg1s\x09TestCharR!!!8S!!!!"s\x09TestOrg2s\x05Morti!!!Dui!!!Eu~\x00\x04Test')

        packet = bot.public_channel_message_ext_msg_handling(packet)

        self.assertEqual("The omni organization TestOrg1 just entered a state of war! TestChar attacked the clan organization TestOrg2's tower in Mort at location (3059,3144).", packet.extended_message.get_message())

    def test_add_packet_handler(self):
        packet_id = 1
        bot = Tyrbot()
        bot.add_packet_handler(packet_id, "handler20", 20)
        bot.add_packet_handler(packet_id, "handler")
        bot.add_packet_handler(packet_id, "handler50", 50)
        bot.add_packet_handler(packet_id, "handler10", 10)
        self.assertEqual(
            [{'priority': 10, 'handler': 'handler10'}, {'priority': 20, 'handler': 'handler20'}, {'priority': 50, 'handler': 'handler'}, {'priority': 50, 'handler': 'handler50'}],
            bot.packet_handlers.get(packet_id))

    def test_remove_packet_handler(self):
        packet_id = 1
        bot = Tyrbot()
        bot.add_packet_handler(packet_id, "handler20", 20)
        bot.add_packet_handler(packet_id, "handler")
        bot.add_packet_handler(packet_id, "handler50", 50)
        bot.add_packet_handler(packet_id, "handler10", 10)
        bot.remove_packet_handler(packet_id, "handler20")
        self.assertEqual(
            [{'priority': 10, 'handler': 'handler10'}, {'priority': 50, 'handler': 'handler'}, {'priority': 50, 'handler': 'handler50'}],
            bot.packet_handlers.get(packet_id))
