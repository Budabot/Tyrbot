from core.decorators import instance, command
from core.command_param_types import Const, Any, Options
from core.chat_blob import ChatBlob


@instance()
class AliasController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        pass

    @command(command="alias", params=[Const("list")], access_level="all",
             description="List command aliases")
    def alias_list_cmd(self, channel, sender, reply, args):
        blob = ""
        data = self.command_alias_service.get_enabled_aliases()
        count = len(data)
        for row in data:
            blob += row.alias + " - " + row.command + "\n"

        return ChatBlob("Aliases (%d)" % count, blob)

    @command(command="alias", params=[Const("add"), Any("alias"), Any("command")], access_level="superadmin",
             description="Add a command alias", sub_command="modify")
    def alias_add_cmd(self, channel, sender, reply, args):
        alias = args[1]
        command = args[2]
        if self.command_alias_service.add_alias(alias, command):
            return "Alias <highlight>%s<end> for command <highlight>%s<end> added successfully." % (alias, command)
        else:
            return "Cannot add alias <highlight>%s<end> since there is already an active alias with that name." % alias

    @command(command="alias", params=[Options(["rem", "remove"]), Any("alias")], access_level="superadmin",
             description="Remove a command alias", sub_command="modify")
    def alias_remove_cmd(self, channel, sender, reply, args):
        alias = args[1]
        if self.command_alias_service.remove_alias(alias):
            return "Alias <highlight>%s<end> has been removed successfully." % alias
        else:
            return "Could not find alias <highlight>%s<end>." % alias
