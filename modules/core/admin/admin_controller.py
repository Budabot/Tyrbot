import hjson

from core.decorators import instance, command
from core.chat_blob import ChatBlob
from core.command_param_types import Any, Const, Options, Character
from core.admin.admin_service import AdminService
from core.translation_service import TranslationService


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
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.getresp = self.ts.get_response

    def start(self):
        self.command_alias_service.add_alias("adminlist", "admin")
        self.command_alias_service.add_alias("admins", "admin")
        self.ts.register_translation("module/admin", self.load_admin_msg)

    def load_admin_msg(self):
        with open("modules/core/admin/admin.msg", mode="r", encoding="UTF-8") as f:
            return hjson.load(f)

    @command(command="admin", params=[], access_level="all",
             description="Show the admin list")
    def admin_list_cmd(self, request):
        admins = self.admin_service.get_all()

        blob = ""
        current_access_level = ""
        for row in admins:
            if row.access_level != current_access_level:
                blob += "\n<header2>%s<end>\n" % row.access_level.capitalize()
                current_access_level = row.access_level

            blob += row.name
            if self.buddy_service.is_online(row.char_id):
                blob += " [<green>Online<end>]"
            blob += "\n"

        return ChatBlob("Admin List (%d)" % len(admins), blob)

    @command(command="admin", params=[Const("add"), Character("character")], access_level="superadmin",
             description="Add an admin", sub_command="modify")
    def admin_add_cmd(self, request, _, char):
        if not char.char_id:
            return self.getresp("global", "char_not_found", {"char": char.name})

        if self.admin_service.add(char.char_id, AdminService.ADMIN):
            return self.getresp("module/admin", "add_success", {"char": char.name, "rank": AdminService.ADMIN})
        else:
            return self.getresp("module/admin", "add_fail", {"char": char.name, "rank": AdminService.ADMIN})

    @command(command="admin", params=[Options(["remove", "rem"]), Character("character")], access_level="superadmin",
             description="Remove an admin", sub_command="modify")
    def admin_remove_cmd(self, request, _, char):
        if not char.char_id:
            return self.getresp("global", "char_not_found", {"char": char.name})

        if self.admin_service.remove(char.char_id):
            return self.getresp("module/admin", "rem_success", {"char": char.name, "rank": AdminService.ADMIN})
        else:
            return self.getresp("module/admin", "rem_fail", {"char": char.name, "rank": AdminService.ADMIN})

    @command(command="moderator", params=[Const("add"), Character("character")], access_level="admin",
             description="Add a moderator", sub_command="modify")
    def moderator_add_cmd(self, request, _, char):
        if not char.char_id:
            return self.getresp("global", "char_not_found", {"char": char.name})

        if self.admin_service.add(char.char_id, AdminService.MODERATOR):
            return self.getresp("module/admin", "add_success", {"char": char.name, "rank": AdminService.MODERATOR})
        else:
            return self.getresp("module/admin", "add_fail", {"char": char.name, "rank": AdminService.MODERATOR})

    @command(command="moderator", params=[Options(["remove", "rem"]), Character("character")], access_level="admin",
             description="Remove a moderator", sub_command="modify")
    def moderator_remove_cmd(self, request, _, char):
        if not char.char_id:
            return self.getresp("global", "char_not_found", {"char": char.name})

        if self.admin_service.remove(char.char_id):
            return self.getresp("module/admin", "rem_success", {"char": char.name, "rank": AdminService.MODERATOR})
        else:
            return self.getresp("module/admin", "rem_fail", {"char": char.name, "rank": AdminService.MODERATOR})
