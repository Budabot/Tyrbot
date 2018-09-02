import unittest

from core.aochat.extended_message import ExtendedMessage
from core.aochat.server_packets import PublicChannelMessage
from modules.standard.tower.tower_controller import TowerController


class TowerControllerTest(unittest.TestCase):

    def test_get_attack_event(self):
        tower_controller = TowerController()

        packet1 = PublicChannelMessage(42949672960, 0, "Tyrence just attacked the neutral organization Test Org's tower in Varmint Woods at location (123, 456).\n", '')

        attack_event1 = tower_controller.get_attack_event(packet1)
        self.assertEqual({'attacker': {'name': 'Tyrence', 'faction': '', 'org_name': ''},
                          'defender': {'faction': 'Neutral', 'org_name': 'Test Org'},
                          'location': {'playfield': {'long_name': 'Varmint Woods'}, 'x_coord': '123', 'y_coord': '456'}},
                         attack_event1)

    def test_get_victory_event(self):
        tower_controller = TowerController()

        packet1 = PublicChannelMessage(42949672962, 0, 'Notum Wars Update: Victory to the Clans!!!', '\x02\x01')
        victory_event1 = tower_controller.get_victory_event(packet1)
        self.assertIsNone(victory_event1)

        packet2 = PublicChannelMessage(42949672962,
                                       0,
                                       "The Neutral organization Test Org Attacker attacked the Neutral Test Org Defender at their base in Varmint Woods. The attackers won!!",
                                       '\x02\x01')
        victory_event2 = tower_controller.get_victory_event(packet2)
        self.assertEqual({'type': 'attack',
                          'winner': {'faction': 'Neutral', 'org_name': 'Test Org Attacker'},
                          'loser': {'faction': 'Neutral', 'org_name': 'Test Org Defender'},
                          'location': {'playfield': {'long_name': 'Varmint Woods'}}},
                         victory_event2)

        packet3 = PublicChannelMessage(42949672962, 0, '~&!!!&r#g1+3R!!!8S!!!!#s\x11Test Organization\x0cOmni Forest~', '\x02\x01')
        packet3.extended_message = ExtendedMessage(506, 147506468, 'Notum Wars Update: The %s organization %s lost their base in %s.', ['omni', 'Test Organization', 'Omni Forest'])
        victory_event3 = tower_controller.get_victory_event(packet3)
        self.assertEqual({'type': 'terminated',
                          'winner': {'faction': 'Omni', 'org_name': 'Test Organization'},
                          'loser': {'faction': 'Omni', 'org_name': 'Test Organization'},
                          'location': {'playfield': {'long_name': 'Omni Forest'}}},
                         victory_event3)
