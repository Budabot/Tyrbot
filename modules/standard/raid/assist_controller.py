from core.decorators import instance, command
from core.command_param_types import Any, Const, Options
from .leader_controller import LeaderController


@instance()
class AssistController:
    def inject(self, registry):
        self.leader_controller = registry.get_instance("leader_controller")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("caller", "assist")
        self.command_alias_service.add_alias("callers", "assist")

    @command(command="assist", params=[], access_level="all",
             description="Show current assist targets")
    def assist_command(self, request):
        return self.get_assist_output(request.conn)

    @command(command="assist", params=[Const("clear")], access_level="all",
             description="Clear all assist targets", sub_command="modify")
    def assist_clear_command(self, request, _):
        if not request.conn.data.get("assist"):
            return "No assist targets set."

        if not self.leader_controller.can_use_command(request.sender.char_id, request.conn):
            return LeaderController.NOT_LEADER_MSG
        else:
            request.conn.data.assist = None
            return "Assist targets have been cleared."

    @command(command="assist", params=[Options(["rem", "remove"]), Any("assist_targets")], access_level="all",
             description="Remove one or more assist targets", sub_command="modify", extended_description="Multiple assist targets should be space-delimited")
    def assist_rem_command(self, request, _, assist_targets):
        targets = assist_targets.split(" ")

        if not self.leader_controller.can_use_command(request.sender.char_id, request.conn):
            return LeaderController.NOT_LEADER_MSG
        else:
            assist = request.conn.data.get("assist") or []
            for target in targets:
                target = target.capitalize()
                if target in assist:
                    self.remove_assist(target, request.conn)
            return self.get_assist_output(request.conn)

    @command(command="assist", params=[Const("add", is_optional=True), Any("assist_targets")], access_level="all",
             description="Add one or more assist targets", sub_command="modify", extended_description="Multiple assist targets should be space-delimited")
    def assist_set_command(self, request, _, assist_targets):
        targets = assist_targets.split(" ")

        if not self.leader_controller.can_use_command(request.sender.char_id, request.conn):
            return LeaderController.NOT_LEADER_MSG
        else:
            assist = request.conn.data.get("assist") or []
            for target in targets:
                target = target.capitalize()
                if target not in assist:
                    self.add_assist(target, request.conn)
            return self.get_assist_output(request.conn)

    def add_assist(self, target, conn):
        assist = conn.data.get("assist")
        if assist:
            assist.append(target)
        else:
            conn.data.assist = [target]

    def remove_assist(self, target, conn):
        assist = conn.data.get("assist")
        if assist:
            assist.remove(target)

    def get_assist_output(self, conn):
        assist = conn.data.get("assist")
        if not assist:
            return "No assist targets set."

        return "/macro assist " + " \\n ".join(map(lambda x: "/assist " + x, reversed(assist)))
