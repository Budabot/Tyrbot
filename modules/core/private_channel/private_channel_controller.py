from core.ban_service import BanService
from core.command_param_types import Character
from core.decorators import instance, command, event


@instance()
class PrivateChannelController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.private_channel_service = registry.get_instance("private_channel_service")
        self.character_service = registry.get_instance("character_service")
        self.job_scheduler = registry.get_instance("job_scheduler")
        self.access_service = registry.get_instance("access_service")

    @command(command="join", params=[], access_level="all",
             description="Join the private channel")
    def join_cmd(self, request):
        self.private_channel_service.invite(request.sender.char_id)

    @command(command="leave", params=[], access_level="all",
             description="Leave the private channel")
    def leave_cmd(self, request):
        self.private_channel_service.kick(request.sender.char_id)

    @command(command="invite", params=[Character("character")], access_level="all",
             description="Invite a character to the private channel")
    def invite_cmd(self, request, char):
        if char.char_id:
            if self.private_channel_service.in_private_channel(char.char_id):
                return "<highlight>%s<end> is already in the private channel." % char.name
            else:
                self.bot.send_private_message(char.char_id, "You have been invited to the private channel by <highlight>%s<end>." % request.sender.name)
                self.private_channel_service.invite(char.char_id)
                return "You have invited <highlight>%s<end> to the private channel." % char.name
        else:
            return "Could not find character <highlight>%s<end>." % char.name

    @command(command="kick", params=[Character("character")], access_level="admin",
             description="Kick a character from the private channel")
    def kick_cmd(self, request, char):
        if char.char_id:
            if not self.private_channel_service.in_private_channel(char.char_id):
                return "<highlight>%s<end> is not in the private channel." % char.name
            else:
                # TODO use request.sender.access_level and char.access_level
                if self.access_service.has_sufficient_access_level(request.sender.char_id, char.char_id):
                    self.bot.send_private_message(char.char_id, "You have been kicked from the private channel by <highlight>%s<end>." % request.sender.name)
                    self.private_channel_service.kick(char.char_id)
                    return "You have kicked <highlight>%s<end> from the private channel." % char.name
                else:
                    return "You do not have the required access level to kick <highlight>%s<end>." % char.name
        else:
            return "Could not find character <highlight>%s<end>." % char.name

    @command(command="kickall", params=[], access_level="admin",
             description="Kick all characters from the private channel")
    def kickall_cmd(self, request):
        self.bot.send_private_channel_message("Everyone will be kicked from this channel in 10 seconds. [by <highlight>%s<end>]" % request.sender.name)
        self.job_scheduler.delayed_job(lambda t: self.private_channel_service.kickall(), 10)

    @event(event_type=BanService.BAN_ADDED_EVENT, description="Kick characters from the private channel who are banned")
    def ban_added_event(self, event_type, event_data):
        self.private_channel_service.kick(event_data.char_id)
