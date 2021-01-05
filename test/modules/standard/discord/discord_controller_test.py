import unittest
from modules.standard.discord.discord_controller import DiscordController


class DiscordControllerTest(unittest.TestCase):

    def test_format_message(self):
        discord_controller = DiscordController()

        msg = "Title <header2>Header<end> <highlight>message<end>"

        self.assertEqual("Title ```yaml\nHeader\n``` `message`", discord_controller.format_message(msg))
