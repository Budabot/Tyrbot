import unittest
from modules.standard.discord.discord_controller import DiscordController


class DiscordControllerTest(unittest.TestCase):

    def test_format_message(self):
        discord_controller = DiscordController()

        msg = "Title <header2>Header</header2> <highlight>message</highlight>"

        self.assertEqual("Title ```yaml\nHeader\n``` `message`", discord_controller.format_message(msg))
