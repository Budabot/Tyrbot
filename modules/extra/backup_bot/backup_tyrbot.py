from core.tyrbot import Tyrbot
from core.decorators import instance


@instance("bot", override=True)
class BackupTyrbot(Tyrbot):
    def inject(self, registry):
        super().inject(registry)
        self.backup_bot_controller = registry.get_instance("backup_bot_controller", is_optional=True)

    def send_org_message(self, msg, add_color=True, conn=None):
        if not self.backup_bot_controller.is_enabled():
            return

        super().send_org_message(msg, add_color=add_color, conn=conn)
        
    def send_private_message(self, char_id, msg, add_color=True, conn=None):
        if not self.backup_bot_controller.is_enabled() and not self.backup_bot_controller.is_processing_command():
            return

        super().send_private_message(char_id, msg, add_color=add_color, conn=conn)
