import unittest
from modules.standard.raffle.raffle_controller import RaffleController


class RaffleControllerTest(unittest.TestCase):

    def test_calc_cmd(self):
        raffle_controller = RaffleController()

        self.assertEqual("testing", raffle_controller.get_item_name("testing"))
        self.assertEqual("this is an item!", raffle_controller.get_item_name("<a href=\"itemref://12345/67890/100\">this is an item!</a>"))
