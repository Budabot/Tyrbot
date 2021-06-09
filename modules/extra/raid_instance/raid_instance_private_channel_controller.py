from core.command_param_types import Character
from core.decorators import instance, command
from modules.core.private_channel.private_channel_controller import PrivateChannelController


@instance("private_channel_controller", override=True)
class RaidInstancePrivateChannelController(PrivateChannelController):
    @command(command="join", params=[], access_level="member",
             description="Join the private channel")
    def join_cmd(self, request):
        self.private_channel_service.invite(request.sender.char_id, request.conn)

    @command(command="leave", params=[], access_level="all",
             description="Leave the private channel")
    def leave_cmd(self, request):
        self.private_channel_service.kick(request.sender.char_id, request.conn)

    @command(command="invite", params=[Character("character")], access_level="all",
             description="Invite a character to the private channel")
    def invite_cmd(self, request, char):
        if char.char_id:
            conn = request.conn
            if char.char_id in conn.private_channel:
                return self.getresp("module/private_channel", "invite_fail", {"target": char.name})
            else:
                self.bot.send_private_message(char.char_id,
                                              self.getresp("module/private_channel", "invite_success_target",
                                                           {"inviter": request.sender.name}),
                                              conn=conn)
                self.private_channel_service.invite(char.char_id, conn)
                return self.getresp("module/private_channel", "invite_success_self", {"target": char.name})
        else:
            return self.getresp("global", "char_not_found", {"char": char.name})

    @command(command="kick", params=[Character("character")], access_level="moderator",
             description="Kick a character from the private channel")
    def kick_cmd(self, request, char):
        if char.char_id:
            conn = request.conn
            if char.char_id not in conn.private_channel:
                return self.getresp("module/private_channel", "kick_fail_not_in_priv", {"target": char.name})
            else:
                # TODO use request.sender.access_level and char.access_level
                if self.access_service.has_sufficient_access_level(request.sender.char_id, char.char_id):
                    self.bot.send_private_message(char.char_id,
                                                  self.getresp("module/private_channel", "kick_success_target",
                                                               {"kicker": request.sender.name}),
                                                  conn=conn)
                    self.private_channel_service.kick(char.char_id, conn)
                    return self.getresp("module/private_channel", "kick_success_self", {"target": char.name})
                else:
                    return self.getresp("module/private_channel", "kick_fail", {"target": char.name})
        else:
            return self.getresp("global", "char_not_found", {"char": char.name})

    @command(command="kickall", params=[], access_level="moderator",
             description="Kick all characters from the private channel")
    def kickall_cmd(self, request):
        conn = request.conn
        self.bot.send_private_channel_message(
            self.getresp("module/private_channel", "kick_all", {"char": request.sender.name}), conn=conn)
        self.job_scheduler.delayed_job(lambda t: self.private_channel_service.kickall(conn), 10)
