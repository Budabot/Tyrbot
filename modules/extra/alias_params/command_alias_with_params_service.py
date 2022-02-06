from core.command_alias_service import CommandAliasService
from core.decorators import instance


@instance("command_alias_service", override=True)
class CommandAliasServiceWithParams(CommandAliasService):
    def get_alias_command_str(self, command_str, command_args):
        row = self.get_alias(command_str)
        if row and row.enabled:
            #print(f"command args '{command_args}'")
            aliased_command = row.command

            if command_args:
                command_args = command_args.lstrip()
                aliased_command = aliased_command.replace("{0}", command_args)
                for i, arg in enumerate(command_args.split(" "), start=1):
                    aliased_command = aliased_command.replace(f"{{{i}}}", arg)

                # if there are no positional arguments, append the command args to the end
                if aliased_command == row.command:
                    aliased_command += " " + command_args
            #print(f"'{aliased_command}'")
            return aliased_command
        else:
            return None
