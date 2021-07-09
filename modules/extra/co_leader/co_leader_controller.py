import time

from core.command_param_types import Const, Character, Options
from core.decorators import instance, command, timerevent, event
from core.private_channel_service import PrivateChannelService
from core.public_channel_service import PublicChannelService
from core.setting_types import ColorSettingType
from modules.core.org_members.org_member_controller import OrgMemberController
from modules.standard.raid.leader_controller import LeaderController


@instance("leader_controller", override=True)
class CoLeaderController(LeaderController):
    def start(self):
        super().start()
        self.setting_service.register(self.module_name, "co_leader_echo_color", "#FFD700", ColorSettingType(), "Color with which the co-leader's messages will be echoed with")

    @command(command="leader", params=[], access_level="all",
             description="Show the current raid leaders and co-leaders")
    def leader_show_command(self, request):
        leader = self.get_leader(request.conn)
        msg = ""
        if leader:
            on_off = "on" if request.conn.data.get("leader_echo") else "off"
            msg += "<highlight>%s</highlight> is set as leader, " % leader.name
            msg += "leader echo is <highlight>%s</highlight>." % on_off
        else:
            msg += self.NO_CURRENT_LEADER_MSG

        co_leaders = self.get_co_leaders(request.conn)
        if co_leaders:
            msg += " Co-leaders: <highlight>%s</highlight>" % ", ".join(map((lambda x: x.name), co_leaders.values()))
        return msg

    @command(command="leader", params=[Const("clear")], access_level="all",
             description="Clear the current raid leader and co-leaders")
    def leader_clear_command(self, request, _):
        if not self.can_use_command(request.sender.char_id, request.conn):
            return self.NOT_LEADER_MSG
        else:
            self.clear_co_leaders(request.conn)
            return self.set_raid_leader(request.sender, None, request.conn)

    @command(command="leader", params=[Const("add"), Character("character")], access_level="all",
             description="Add a co-leader")
    def leader_add_command(self, request, _, char):
        if not char.char_id:
            return "Could not find character <highlight>%s</highlight>." % char.name

        if not self.can_use_command(request.sender.char_id, request.conn):
            return self.NOT_LEADER_MSG

        leader = self.get_leader(request.conn)
        if leader and char.char_id == leader.char_id:
            return "<highlight>%s</highlight> is already the leader and cannot be set as a co-leader." % char.name

        if self.is_co_leader(char.char_id, request.conn):
            return "<highlight>%s</highlight> is already a co-leader." % char.name

        self.add_co_leader(char, request.conn)
        return "<highlight>%s</highlight> has been added as a co-leader." % char.name

    @command(command="leader", params=[Options(["remove", "rem"]), Character("character")], access_level="all",
             description="Remove a co-leader")
    def leader_remove_command(self, request, _, char):
        if not char.char_id:
            return "Could not find character <highlight>%s</highlight>." % char.name

        if not self.can_use_command(request.sender.char_id, request.conn):
            return self.NOT_LEADER_MSG

        if not self.is_co_leader(char.char_id, request.conn):
            return "<highlight>%s</highlight> is not a co-leader." % char.name

        self.remove_co_leader(char, request.conn)
        return "<highlight>%s</highlight> has been removed as a co-leader." % char.name

    @timerevent(budatime="1h", description="Remove raid leader and all co-leaders if raid leader hasn't been active for more than 1 hour")
    def leader_auto_remove(self, event_type, event_data):
        for _id, conn in self.bot.get_conns():
            last_activity = conn.data.get("leader_last_activity")
            if last_activity:
                if last_activity - int(time.time()) > 3600:
                    self.clear_leader(conn)
                    self.clear_co_leaders(conn)
                    self.raid_controller.send_message("Raid leader and all co-leaders have been automatically cleared because of inactivity.", conn)

    @event(PrivateChannelService.LEFT_PRIVATE_CHANNEL_EVENT, "Remove co-leader if co-leader leaves private channel")
    def co_leader_remove_on_leave_private(self, event_type, event_data):
        if self.is_co_leader(event_data.char_id, event_data.conn):
            self.remove_co_leader(event_data.char_id, event_data.conn)
            self.raid_controller.send_message(f"{event_data.name} left private channel and has been automatically removed as co-leader.",
                                              event_data.conn)

    @event(OrgMemberController.ORG_MEMBER_LOGOFF_EVENT, "Remove co-leader if co-leader logs off")
    def co_leader_remove_on_logoff(self, event_type, event_data):
        # fix for when buddy logs off before conn knows what org it belongs to
        if not event_data.conn:
            return

        if self.is_co_leader(event_data.char_id, event_data.conn):
            self.remove_co_leader(event_data.char_id, event_data.conn)
            self.raid_controller.send_message("%s has logged off and has been removed as co-leader." % event_data.name,
                                              event_data.conn)

    @event(PrivateChannelService.PRIVATE_CHANNEL_MESSAGE_EVENT, "Echo co-leader messages from private channel", is_hidden=True)
    def co_leader_echo_private_event(self, event_type, event_data):
        if event_data.conn.data.get("leader_echo") and self.is_co_leader(event_data.char_id, event_data.conn):
            if not event_data.message.startswith(self.setting_service.get("symbol").get_value()):
                self.co_leader_echo(event_data.char_id, event_data.message, PrivateChannelService.PRIVATE_CHANNEL_COMMAND, conn=event_data.conn)

    @event(PublicChannelService.ORG_CHANNEL_MESSAGE_EVENT, "Echo co-leader messages from org channel", is_hidden=True)
    def co_leader_echo_org_event(self, event_type, event_data):
        if event_data.conn.data.get("leader_echo") and self.is_co_leader(event_data.char_id, event_data.conn):
            if not event_data.message.startswith(self.setting_service.get("symbol").get_value()):
                self.co_leader_echo(event_data.char_id, event_data.message, PublicChannelService.ORG_CHANNEL_COMMAND, event_data.conn)

    def co_leader_echo(self, char_id, message, channel, conn):
        sender = self.character_service.resolve_char_to_name(char_id)
        color = self.setting_service.get("co_leader_echo_color")

        if channel == PublicChannelService.ORG_CHANNEL_COMMAND:
            self.bot.send_org_message("%s: %s" % (sender, color.format_text(message)), conn=conn)
        elif channel == PrivateChannelService.PRIVATE_CHANNEL_COMMAND:
            self.bot.send_private_channel_message("%s: %s" % (sender, color.format_text(message)), conn=conn)

        self.activity_done(conn)

    def is_co_leader(self, char_id, conn):
        return char_id in conn.data.get("co_leaders", {})

    def can_use_command(self, char_id, conn):
        leader = self.get_leader(conn)
        if not leader or self.access_service.has_sufficient_access_level(char_id, leader.char_id) \
                or self.is_co_leader(char_id, conn):
            self.activity_done(conn)
            return True

        return False

    def set_leader(self, sender, conn):
        super().set_leader(sender, conn)
        if self.is_co_leader(sender.char_id, conn):
            self.remove_co_leader(sender.char_id, conn)

    def get_co_leaders(self, conn):
        return conn.data.get("co_leaders", {})

    def clear_co_leaders(self, conn):
        conn.data.co_leaders = {}

    def add_co_leader(self, sender, conn):
        co_leaders = conn.data.get("co_leaders", {})
        co_leaders[sender.char_id] = sender
        conn.data["co_leaders"] = co_leaders

    def remove_co_leader(self, char_id, conn):
        co_leaders = conn.data.get("co_leaders", {})
        del co_leaders[char_id]
        conn.data["co_leaders"] = co_leaders
