import unittest
from modules.standard.helpbot.calculator_controller import CalculatorController


class CalculatorControllerTest(unittest.TestCase):

    def test_calc_cmd(self):
        calculator_controller = CalculatorController()

        self.assertEqual("1 + 1 = 2", calculator_controller.calc_cmd(None, "1 + 1"))
        self.assertEqual("1+1 = 2", calculator_controller.calc_cmd(None, "1+1"))
        self.assertEqual("10*3 = 30", calculator_controller.calc_cmd(None, "10*3"))
        self.assertEqual("10/3 = 3.3333", calculator_controller.calc_cmd(None, "10/3"))
        self.assertEqual("10%3 = 1", calculator_controller.calc_cmd(None, "10%3"))
        self.assertEqual("(1+2)*3 = 9", calculator_controller.calc_cmd(None, "(1+2)*3"))
        self.assertEqual("3**3 = 27", calculator_controller.calc_cmd(None, "3**3"))
        self.assertEqual("10//3 = 3", calculator_controller.calc_cmd(None, "10//3"))
        self.assertEqual("4&1 = 0", calculator_controller.calc_cmd(None, "4&1"))
        self.assertEqual("4|1 = 5", calculator_controller.calc_cmd(None, "4|1"))
        self.assertEqual("~10 = -11", calculator_controller.calc_cmd(None, "~10"))
        self.assertEqual("10 << 1 = 20", calculator_controller.calc_cmd(None, "10 << 1"))
        self.assertEqual("10 >> 1 = 5", calculator_controller.calc_cmd(None, "10 >> 1"))
        self.assertEqual("Invalid character detected.", calculator_controller.calc_cmd(None, "1 + 1 = 2f"))
        self.assertEqual("Invalid formula supplied.", calculator_controller.calc_cmd(None, "10+-&"))
