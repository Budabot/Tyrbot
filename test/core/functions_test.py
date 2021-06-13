import unittest
import core.functions
from core.logger import Logger


class FunctionsTest(unittest.TestCase):

    def test_get_config_from_env(self):
        config = {"TYRBOT_BOTS_1_USERNAME": "username",
                  "TYRBOT_BOTS_1_PASSWORD": "password",
                  "TYRBOT_BOTS_1_CHARACTER": "character",
                  "TYRBOT_BOTS_1_IS-MAIN": "true"}

        logger = Logger("test")

        result = core.functions.get_config_from_env(config, logger)
        expected = {'bots': {'1': {'username': 'username', 'password': 'password', 'character': 'character', 'is_main': True}}}

        self.assertEqual(expected, result)
