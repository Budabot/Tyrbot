from core.decorators import instance, command, event
from core.command_param_types import Any
from core.private_channel_manager import PrivateChannelManager


@instance()
class PrivateChannelController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.private_channel_manager = registry.get_instance("private_channel_manager")
        self.character_manager = registry.get_instance("character_manager")
        self.job_scheduler = registry.get_instance("job_scheduler")
        self.access_manager = registry.get_instance("access_manager")

    @command(command="join", params=[], access_level="all",
             description="Join the private channel")
    def join_cmd(self, channel, sender, reply, args):
        self.private_channel_manager.invite(sender.char_id)

    @command(command="leave", params=[], access_level="all",
             description="Leave the private channel")
    def leave_cmd(self, channel, sender, reply, args):
        self.private_channel_manager.kick(sender.char_id)

    @command(command="invite", params=[Any("character")], access_level="all",
             description="Invite a character to the private channel")
    def invite_cmd(self, channel, sender, reply, args):
        char = args[0].capitalize()
        char_id = self.character_manager.resolve_char_to_id(char)
        if char_id:
            if self.private_channel_manager.in_private_channel(char_id):
                reply("<highlight>%s<end> is already in the private channel." % char)
            else:
                self.bot.send_private_message(char_id, "You have been invited to the private channel by <highlight>%s<end>." % sender.name)
                self.private_channel_manager.invite(char_id)
                reply("You have invited <highlight>%s<end> to the private channel." % char)
        else:
            reply("Could not find character <highlight>%s<end>." % char)

    @command(command="kick", params=[Any("character")], access_level="admin",
             description="Kick a character from the private channel")
    def kick_cmd(self, channel, sender, reply, args):
        char = args[0].capitalize()
        char_id = self.character_manager.resolve_char_to_id(char)
        if char_id:
            if not self.private_channel_manager.in_private_channel(char_id):
                reply("<highlight>%s<end> is not in the private channel." % char)
            else:
                if self.access_manager.compare_char_access_levels(sender.char_id, char_id) > 0:
                    self.bot.send_private_message(char_id, "You have been kicked from the private channel by <highlight>%s<end>." % sender.name)
                    self.private_channel_manager.kick(char_id)
                    reply("You have kicked <highlight>%s<end> from the private channel." % char)
                else:
                    reply("You do not have the required access level to kick <highlight>%s<end>." % char)
        else:
            reply("Could not find character <highlight>%s<end>." % char)

    @command(command="kickall", params=[], access_level="admin",
             description="Kick all characters from the private channel")
    def kickall_cmd(self, channel, sender, reply, args):
        self.bot.send_private_channel_message("Everyone will be kicked from this channel in 10 seconds. [by <highlight>%s<end>]" % sender.name)
        self.job_scheduler.delayed_job(lambda t: self.private_channel_manager.kickall(), 10)

    @event(PrivateChannelManager.JOINED_PRIVATE_CHANNEL_EVENT, "Notify private channel when someone joins")
    def private_channel_joined_event(self, event_type, event_data):
        char_name = self.character_manager.get_char_name(event_data.char_id)
        self.bot.send_private_channel_message("<highlight>%s<end> has joined the private channel." % char_name)

    @event(PrivateChannelManager.LEFT_PRIVATE_CHANNEL_EVENT, "Notify private channel when someone leaves")
    def private_channel_left_event(self, event_type, event_data):
        char_name = self.character_manager.get_char_name(event_data.char_id)
        self.bot.send_private_channel_message("<highlight>%s<end> has left the private channel." % char_name)
