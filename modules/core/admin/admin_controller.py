from core.decorators import instance, command, event
from core.chat_blob import ChatBlob
from core.command_param_types import Const, Options, Character
from core.admin_service import AdminService
from core.standard_message import StandardMessage


@instance()
class AdminController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.admin_service = registry.get_instance("admin_service")
        self.pork_service = registry.get_instance("pork_service")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.buddy_service = registry.get_instance("buddy_service")

    def start(self):
        self.command_alias_service.add_alias("adminlist", "admin")
        self.command_alias_service.add_alias("admins", "admin")

    @command(command="admin", params=[], access_level="all",
             description="Show the admin list")
    def admin_list_cmd(self, request):
        admins = self.admin_service.get_all()

        blob = ""
        current_access_level = ""
        for row in admins:
            if row.access_level != current_access_level:
                blob += "\n<header2>%s</header2>\n" % row.access_level.capitalize()
                current_access_level = row.access_level

            if row.name:
                blob += row.name
            else:
                blob += "Unknown(%d)" % row.char_id

            if self.buddy_service.is_online(row.char_id):
                blob += " [<green>Online</green>]"
            blob += "\n"

        return ChatBlob("Admin List (%d)" % len(admins), blob)

    @command(command="admin", params=[Const("add"), Character("character")], access_level="superadmin",
             description="Add an admin", sub_command="modify")
    def admin_add_cmd(self, request, _, char):
        if not char.char_id:
            return StandardMessage.char_not_found(char.name)

        if self.admin_service.add(char.char_id, AdminService.ADMIN):
            return f"Character <highlight>{char.name}</highlight> added as <highlight>{AdminService.ADMIN}</highlight> successfully."
        else:
            return f"Could not add character <highlight>{char.name}</highlight> as <highlight>{AdminService.ADMIN}</highlight>."

    @command(command="admin", params=[Options(["remove", "rem"]), Character("character")], access_level="superadmin",
             description="Remove an admin", sub_command="modify")
    def admin_remove_cmd(self, request, _, char):
        if not char.char_id:
            return StandardMessage.char_not_found(char.name)

        if self.admin_service.remove(char.char_id):
            return f"Character <highlight>{char.name}</highlight> removed as <highlight>{AdminService.ADMIN}</highlight> successfully."
        else:
            return f"Could not remove character <highlight>{char.name}</highlight> as <highlight>{AdminService.ADMIN}</highlight>."

    @command(command="moderator", params=[Const("add"), Character("character")], access_level="admin",
             description="Add a moderator", sub_command="modify")
    def moderator_add_cmd(self, request, _, char):
        if not char.char_id:
            return StandardMessage.char_not_found(char.name)

        if self.admin_service.add(char.char_id, AdminService.MODERATOR):
            return f"Character <highlight>{char.name}</highlight> added as <highlight>{AdminService.MODERATOR}</highlight> successfully."
        else:
            return f"Could not add character <highlight>{char.name}</highlight> as <highlight>{AdminService.MODERATOR}</highlight>."

    @command(command="moderator", params=[Options(["remove", "rem"]), Character("character")], access_level="admin",
             description="Remove a moderator", sub_command="modify")
    def moderator_remove_cmd(self, request, _, char):
        if not char.char_id:
            return StandardMessage.char_not_found(char.name)

        if self.admin_service.remove(char.char_id):
            return f"Character <highlight>{char.name}</highlight> removed as <highlight>{AdminService.MODERATOR}</highlight> successfully."
        else:
            return f"Could not remove character <highlight>{char.name}</highlight> as <highlight>{AdminService.MODERATOR}</highlight>."

    @event(event_type="connect", description="Add admins as buddies", is_system=True)
    def connect_event(self, event_type, event_data):
        for row in self.admin_service.get_all():
            self.buddy_service.add_buddy(row.char_id, "admin")
