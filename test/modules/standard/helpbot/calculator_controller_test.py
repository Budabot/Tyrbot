import unittest
from modules.standard.helpbot.calculator_controller import CalculatorController


class CalculatorControllerTest(unittest.TestCase):

    def test_calc_cmd(self):
        calculator_controller = CalculatorController()

        self.assert_command_reply("1 + 1 = 2", calculator_controller.calc_cmd, None, None, ["1 + 1"])
        self.assert_command_reply("1+1 = 2", calculator_controller.calc_cmd, None, None, ["1+1"])
        self.assert_command_reply("10*3 = 30", calculator_controller.calc_cmd, None, None, ["10*3"])
        self.assert_command_reply("10/3 = 3.3333", calculator_controller.calc_cmd, None, None, ["10/3"])
        self.assert_command_reply("10%3 = 1", calculator_controller.calc_cmd, None, None, ["10%3"])
        self.assert_command_reply("(1+2)*3 = 9", calculator_controller.calc_cmd, None, None, ["(1+2)*3"])
        self.assert_command_reply("3**3 = 27", calculator_controller.calc_cmd, None, None, ["3**3"])
        self.assert_command_reply("10//3 = 3", calculator_controller.calc_cmd, None, None, ["10//3"])
        self.assert_command_reply("4&1 = 0", calculator_controller.calc_cmd, None, None, ["4&1"])
        self.assert_command_reply("4|1 = 5", calculator_controller.calc_cmd, None, None, ["4|1"])
        self.assert_command_reply("~10 = -11", calculator_controller.calc_cmd, None, None, ["~10"])
        self.assert_command_reply("10 << 1 = 20", calculator_controller.calc_cmd, None, None, ["10 << 1"])
        self.assert_command_reply("10 >> 1 = 5", calculator_controller.calc_cmd, None, None, ["10 >> 1"])
        self.assert_command_reply("Invalid character detected.", calculator_controller.calc_cmd, None, None, ["1 + 1 = 2f"])
        self.assert_command_reply("Invalid formula supplied.", calculator_controller.calc_cmd, None, None, ["10+-&"])

    def assert_command_reply(self, expected, command_method, channel, sender, args):
        def reply(x):
            self.assertEqual(x, expected)

        command_method(channel, sender, reply, args)
