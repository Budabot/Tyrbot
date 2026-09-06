from core.decorators import instance, event
from core.setting_types import TextSettingType
from core.buddy_service import BuddyService
from core.dict_object import DictObject


@instance()
class BackupBotController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.setting_service = registry.get_instance("setting_service")
        self.character_service = registry.get_instance("character_service")
        self.buddy_service: BuddyService = registry.get_instance("buddy_service")
        self.command_service = registry.get_instance("command_service")

    def start(self):
        self.setting_service.register(
            self.module_name,
            "backup_main_bot",
            "",
            TextSettingType(options=[], allow_empty=True),
            "Name of the main bot to monitor"
        )
        self.setting_service.register_change_listener("backup_main_bot", self.on_backup_main_bot_change)

        self._is_processing_command = False
        self._is_enabled = True

    def connect(self):
        # Initialize buddy tracking if setting is already configured
        main_bot_name = self.setting_service.get_value("backup_main_bot")
        if main_bot_name:
            self._update_buddy(None, main_bot_name)

    def on_backup_main_bot_change(self, setting_name, old_value, new_value):
        self._update_buddy(old_value, new_value)

    def _update_buddy(self, old_name, new_name):
        if old_name:
            char_id = self.character_service.resolve_char_to_id(old_name)
            if char_id:
                self.buddy_service.remove_buddy(char_id, "backup_bot")

        if new_name:
            char_id = self.character_service.resolve_char_to_id(new_name)
            if char_id:
                self.buddy_service.add_buddy(char_id, "backup_bot")
                self._is_enabled = not bool(self.buddy_service.is_online(char_id))

    def _is_main_bot_char_id(self, char_id: int) -> bool:
        main_bot_name = self.setting_service.get_value("backup_main_bot")
        if not main_bot_name:
            return False
        main_bot_char_id = self.character_service.resolve_char_to_id(main_bot_name)
        return char_id == main_bot_char_id

    def is_enabled(self) -> bool:
        return self._is_enabled
        
    def is_processing_command(self) -> bool:
        return self._is_processing_command

    @event(event_type=BuddyService.BUDDY_LOGON_EVENT, description="Track main bot logon", is_system=True)
    def handle_buddy_logon(self, event_type, event_data):
        if self._is_main_bot_char_id(event_data.char_id):
            self._is_enabled = False

    @event(event_type=BuddyService.BUDDY_LOGOFF_EVENT, description="Track main bot logoff", is_system=True)
    def handle_buddy_logoff(self, event_type, event_data):
        if self._is_main_bot_char_id(event_data.char_id):
            self._is_enabled = True

    def set_processing_command(self, is_processing: bool):
        self._is_processing_command = is_processing
