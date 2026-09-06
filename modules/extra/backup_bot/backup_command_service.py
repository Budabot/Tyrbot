from core.command_service import CommandService
from core.decorators import instance


@instance("command_service", override=True)
class BackupCommandService(CommandService):
    def inject(self, registry):
        super().inject(registry)
        self.backup_bot_controller = registry.get_instance("backup_bot_controller", is_optional=True)

    def process_command(self, message: str, channel: str, char_id, reply, conn):
        if channel == "org" and not self.backup_bot_controller.is_enabled():
            return

        self.backup_bot_controller.set_processing_command(True)
        try:
            return super().process_command(message, channel, char_id, reply, conn)
        finally:
            self.backup_bot_controller.set_processing_command(False)
