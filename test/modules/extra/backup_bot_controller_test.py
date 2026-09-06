import unittest
from unittest.mock import MagicMock
from core.registry import Registry

# Mock Registry before importing modules that use decorators accessing Registry
Registry.get_instance = MagicMock()

from modules.extra.backup_bot.backup_bot_controller import BackupBotController
from modules.extra.backup_bot.backup_command_service import BackupCommandService
from modules.extra.backup_bot.backup_tyrbot import BackupTyrbot
from core.dict_object import DictObject


class BackupBotControllerTest(unittest.TestCase):
    def setUp(self):
        self.registry = MagicMock()
        self.bot = BackupTyrbot()
        self.setting_service = MagicMock()
        self.character_service = MagicMock()
        self.buddy_service = MagicMock()
        self.command_service = MagicMock()
        self.command_alias_service = MagicMock()
        self.command_alias_service.get_alias_command_str.return_value = None
        self.access_service = MagicMock()
        self.access_service.get_access_level.return_value = 0

        self.registry.get_instance.side_effect = self._get_instance

        self.controller = BackupBotController()
        self.controller.module_name = "backup_bot"
        self.controller.inject(self.registry)

        self.bot.inject(self.registry)

        self.backup_command_service = BackupCommandService()
        self.backup_command_service.inject(self.registry)

        # Mock default behavior
        self.setting_values = {"backup_main_bot": "MainBot"}
        self.setting_service.get_value.side_effect = lambda name: self.setting_values.get(name, "")

        self.char_map = {"MainBot": 12345, "OldBot": 54321}
        self.character_service.resolve_char_to_id.side_effect = lambda name: self.char_map.get(name, None)

        self.online_buddies = {12345: True}
        self.buddy_service.is_online.side_effect = lambda char_id: self.online_buddies.get(char_id, False)

        # Mock super().send_org_message on BackupTyrbot
        self.orig_send_org_message = MagicMock()
        self.bot.get_primary_conn = MagicMock()
        self.bot.get_text_pages = MagicMock(return_value=[])

        self.controller.start()

    def _get_instance(self, name, is_optional=False):
        mapping = {
            "bot": self.bot,
            "setting_service": self.setting_service,
            "character_service": self.character_service,
            "buddy_service": self.buddy_service,
            "command_service": self.command_service,
            "command_alias_service": self.command_alias_service,
            "access_service": self.access_service,
            "backup_bot_controller": self.controller,
        }
        return mapping.get(name)

    def test_start_registers_settings_and_listeners(self):
        self.setting_service.register.assert_called_once()
        self.setting_service.register_change_listener.assert_called_once_with(
            "backup_main_bot", self.controller.on_backup_main_bot_change
        )
        self.buddy_service.add_buddy.assert_called_with(12345, "backup_bot")

    def test_on_backup_main_bot_change(self):
        self.controller.on_backup_main_bot_change("backup_main_bot", "OldBot", "MainBot")
        self.buddy_service.remove_buddy.assert_called_with(54321, "backup_bot")
        self.buddy_service.add_buddy.assert_called_with(12345, "backup_bot")

    def test_online_main_bot_blocks_org_channel_command(self):
        reply_mock = MagicMock()
        super_process = MagicMock()
        self.backup_command_service.get_command_configs = MagicMock(return_value=[])

        # Test process_command on BackupCommandService
        self.backup_command_service.process_command("!test", "org", 999, reply_mock, None)
        self.assertFalse(self.controller.is_enabled())

    def test_online_main_bot_allows_priv_channel_commands(self):
        reply_mock = MagicMock()
        self.backup_command_service.get_command_configs = MagicMock(return_value=[])
        self.backup_command_service.process_command("!test", "private_channel", 999, reply_mock, None)

    def test_online_main_bot_suppress_non_command_org_message(self):
        self.bot.get_primary_conn.reset_mock()
        self.bot.send_org_message("Direct org message")
        self.bot.get_primary_conn.assert_not_called()

    def test_online_main_bot_allow_command_reply_org_message(self):
        self.bot.get_primary_conn.reset_mock()
        self.backup_command_service.get_command_configs = MagicMock(return_value=[])
        self.backup_command_service.process_command("!test", "private_channel", 999, MagicMock(), None)
        self.assertFalse(self.controller._is_processing_command)

    def test_offline_main_bot_full_functionality(self):
        self.controller.handle_buddy_logoff(None, DictObject({"char_id": 12345}))
        self.assertTrue(self.controller.is_enabled())

        # Command should be allowed in org channel when offline
        self.backup_command_service.get_command_configs = MagicMock(return_value=[])
        self.backup_command_service.process_command("!test", "org", 999, MagicMock(), None)

        # Direct org message should be allowed
        self.bot.get_primary_conn.reset_mock()
        self.bot.send_org_message("Direct org message")
        self.bot.get_primary_conn.assert_called_once()

    def test_logon_logoff_events_update_is_enabled(self):
        self.controller.handle_buddy_logon(None, DictObject({"char_id": 12345}))
        self.assertFalse(self.controller.is_enabled())

        self.controller.handle_buddy_logoff(None, DictObject({"char_id": 12345}))
        self.assertTrue(self.controller.is_enabled())

    def test_empty_setting_full_functionality(self):
        self.setting_values["backup_main_bot"] = ""
        self.controller.on_backup_main_bot_change("backup_main_bot", "MainBot", "")
        self.assertTrue(self.controller.is_enabled())

        # Command should be allowed in org channel
        self.backup_command_service.get_command_configs = MagicMock(return_value=[])
        self.backup_command_service.process_command("!test", "org", 999, MagicMock(), None)

        # Direct org message should be allowed
        self.bot.get_primary_conn.reset_mock()
        self.bot.send_org_message("Direct org message")
        self.bot.get_primary_conn.assert_called_once()
