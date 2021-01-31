from core.decorators import instance, command
from core.command_param_types import Any, Const
from .leader_controller import LeaderController


@instance()
class AssistController:
    def __init__(self):
        self.assist = []

    def inject(self, registry):
        self.leader_controller = registry.get_instance("leader_controller")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("caller", "assist")
        self.command_alias_service.add_alias("callers", "assist")

    @command(command="assist", params=[], access_level="all",
             description="Show current assist targets")
    def assist_command(self, request):
        return self.get_assist_output()

    @command(command="assist", params=[Const("clear")], access_level="all",
             description="Clear all assist targets", sub_command="modify")
    def assist_clear_command(self, request, _):
        if not self.assist:
            return "No assist targets set."

        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG
        else:
            self.assist = []
            return "Assist targets have been cleared."

    @command(command="assist", params=[Const("add", is_optional=True), Any("assist_targets")], access_level="all",
             description="Add one or more assist targets", sub_command="modify", extended_description="Multiple assist targets should be space-delimited")
    def assist_set_command(self, request, _, assist_targets):
        targets = assist_targets.split(" ")

        if not self.leader_controller.can_use_command(request.sender.char_id):
            return LeaderController.NOT_LEADER_MSG
        else:
            for target in targets:
                if target not in self.assist:
                    self.assist.append(target)
            return self.get_assist_output()

    def get_assist_output(self):
        if not self.assist:
            return "No assist targets set."

        return "/macro assist " + " \\n ".join(map(lambda x: "/assist " + x.capitalize(), reversed(self.assist)))
