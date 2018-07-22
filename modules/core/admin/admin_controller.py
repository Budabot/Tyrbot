from core.decorators import instance, command
from core.chat_blob import ChatBlob
from core.command_param_types import Any, Const, Options
from core.admin.admin_service import AdminService


@instance()
class AdminController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.admin_service = registry.get_instance("admin_service")
        self.character_service = registry.get_instance("character_service")
        self.pork_service = registry.get_instance("pork_service")

    @command(command="admin", params=[], access_level="all",
             description="Show the admin list")
    def admin_list_cmd(self, channel, sender, reply, args):
        admins = seld.admin_service.get_all()
        superadmin = self.pork_service.get_character_info(self.bot.superadmin)
        superadmin.access_level = "superadmin"
        admins.insert(0, superadmin)

        blob = ""
        current_access_level = ""
        for row in admins:
            if row.access_level != current_access_level:
                blob += "\n<header2>%s<end>\n" % row.access_level.capitalize()
                current_access_level = row.access_level

            blob += row.name + "\n"

        reply(ChatBlob("Admin List (%d)" % len(admins), blob))

    @command(command="admin", params=[Const("add"), Any("character")], access_level="superadmin",
             description="Add an admin", sub_command="modify")
    def admin_add_cmd(self, channel, sender, reply, args):
        name = args[1].capitalize()
        char_id = self.character_service.resolve_char_to_id(name)

        if not char_id:
            reply("Could not find character <highlight>%s<end>." % name)
            return

        if seld.admin_service.add(char_id, AdminService.ADMIN):
            reply("Character <highlight>%s<end> added as <highlight>%s<end> successfully." % (name, AdminService.ADMIN))
        else:
            reply("Could not add character <highlight>%s<end> as <highlight>%s<end>." % (name, AdminService.ADMIN))

    @command(command="admin", params=[Options(["remove", "rem"]), Any("character")], access_level="superadmin",
             description="Remove an admin", sub_command="modify")
    def admin_remove_cmd(self, channel, sender, reply, args):
        name = args[1].capitalize()
        char_id = self.character_service.resolve_char_to_id(name)

        if not char_id:
            reply("Could not find character <highlight>%s<end>." % name)
            return

        if seld.admin_service.remove(char_id):
            reply("Character <highlight>%s<end> removed as <highlight>%s<end> successfully." % (name, AdminService.ADMIN))
        else:
            reply("Could not remove character <highlight>%s<end> as <highlight>%s<end>." % (name, AdminService.ADMIN))

    @command(command="moderator", params=[Const("add"), Any("character")], access_level="superadmin",
             description="Add a moderator", sub_command="modify")
    def moderator_add_cmd(self, channel, sender, reply, args):
        name = args[1].capitalize()
        char_id = self.character_service.resolve_char_to_id(name)

        if not char_id:
            reply("Could not find character <highlight>%s<end>." % name)
            return

        if seld.admin_service.add(char_id, AdminService.MODERATOR):
            reply("Character <highlight>%s<end> added as <highlight>%s<end> successfully." % (name, AdminService.MODERATOR))
        else:
            reply("Could not add character <highlight>%s<end> as <highlight>%s<end>." % (name, AdminService.MODERATOR))

    @command(command="moderator", params=[Options(["remove", "rem"]), Any("character")], access_level="superadmin",
             description="Remove a moderator", sub_command="modify")
    def moderator_remove_cmd(self, channel, sender, reply, args):
        name = args[1].capitalize()
        char_id = self.character_service.resolve_char_to_id(name)

        if not char_id:
            reply("Could not find character <highlight>%s<end>." % name)
            return

        if seld.admin_service.remove(char_id):
            reply("Character <highlight>%s<end> removed as <highlight>%s<end> successfully." % (name, AdminService.MODERATOR))
        else:
            reply("Could not remove character <highlight>%s<end> as <highlight>%s<end>." % (name, AdminService.MODERATOR))
