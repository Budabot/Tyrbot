from core.decorators import instance, command
from core.command_param_types import Const, Any, Options
from core.chat_blob import ChatBlob


@instance()
class AliasController:
    def inject(self, registry):
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.text = registry.get_instance("text")

    @command(command="alias", params=[Const("list")], access_level="all",
             description="List command aliases")
    def alias_list_cmd(self, request, _):
        data = self.command_alias_service.get_enabled_aliases()
        count = len(data)
        padded_rows = self.text.pad_table(list(map(lambda row: [row.alias, row.command], data)))

        blob = ""
        for cols in padded_rows:
            blob += "  ".join(cols) + "\n"

        return ChatBlob(f"Aliases ({count})", blob)

    @command(command="alias", params=[Const("add"), Any("alias"), Any("command")], access_level="admin",
             description="Add a command alias", sub_command="modify")
    def alias_add_cmd(self, request, _, alias, command_str):
        if self.command_alias_service.add_alias(alias, command_str, force_enable=True):
            return f"Alias <highlight>{alias}</highlight> for command <highlight>{command_str}</highlight> added successfully."
        else:
            return f"Cannot add alias <highlight>{alias}</highlight> since there is already an active alias with that name."

    @command(command="alias", params=[Options(["rem", "remove"]), Any("alias")], access_level="admin",
             description="Remove a command alias", sub_command="modify")
    def alias_remove_cmd(self, request, _, alias):
        if self.command_alias_service.remove_alias(alias):
            return f"Alias <highlight>{alias}</highlight> has been removed successfully."
        else:
            return f"Could not find alias <highlight>{alias}</highlight>."
