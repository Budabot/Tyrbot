from core.decorators import instance, command, event
from core.command_param_types import Any, Character
from core.private_channel_service import PrivateChannelService


@instance()
class PocketbossController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.private_channel_service = registry.get_instance("private_channel_service")
        self.character_service = registry.get_instance("character_service")
        self.job_scheduler = registry.get_instance("job_scheduler")
        self.access_service = registry.get_instance("access_service")

    @command(command="pocketboss", params=[], access_level="all",
             description="Join the private channel")
    def pocketboss_cmd(self, request):
        self.private_channel_service.invite(request.sender.char_id)