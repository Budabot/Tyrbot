from core.decorators import instance, command
from core.command_param_types import Const, Any, Options
from core.chat_blob import ChatBlob
from core.translation_service import TranslationService


@instance()
class AliasController:
    def inject(self, registry):
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.getresp = self.ts.get_response

    @command(command="alias", params=[Const("list")], access_level="all",
             description="List command aliases")
    def alias_list_cmd(self, request, _):
        blob = ""
        data = self.command_alias_service.get_enabled_aliases()
        count = len(data)
        for row in data:
            blob += row.alias + " - " + row.command + "\n"

        return ChatBlob(self.getresp("module/config", "alias_blob_title", {"amount":count}), blob)

    @command(command="alias", params=[Const("add"), Any("alias"), Any("command")], access_level="admin",
             description="Add a command alias", sub_command="modify")
    def alias_add_cmd(self, request, _, alias, command_str):
        if self.command_alias_service.add_alias(alias, command_str, force_enable=True):
            return self.getresp("module/config", "alias_add_success", {"alias": alias, "cmd": command_str})
        else:
            return self.getresp("module/config", "alias_add_fail", {"alias": alias})

    @command(command="alias", params=[Options(["rem", "remove"]), Any("alias")], access_level="admin",
             description="Remove a command alias", sub_command="modify")
    def alias_remove_cmd(self, request, _, alias):
        if self.command_alias_service.remove_alias(alias):
            return self.getresp("module/config", "alias_rem_success", {"alias": alias})
        else:
            return self.getresp("module/config", "alias_rem_fail", {"alias": alias})
