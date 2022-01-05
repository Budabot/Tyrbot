from core.alts_service import AltsService
from core.chat_blob import ChatBlob
from core.command_param_types import Const, Options, Character, Multiple
from core.decorators import instance, command
from core.standard_message import StandardMessage


@instance()
class AltsController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.alts_service: AltsService = registry.get_instance("alts_service")
        self.buddy_service = registry.get_instance("buddy_service")
        self.util = registry.get_instance("util")

    @command(command="alts", params=[], access_level="all",
             description="Show your alts")
    def alts_list_cmd(self, request):
        alts = self.alts_service.get_alts(request.sender.char_id)
        blob = self.format_alt_list(alts)

        return ChatBlob(f"Alts of {alts[0].name} ({len(alts)})", blob)

    def get_alt_status(self, status):
        if status == AltsService.MAIN:
            return " - [main]"
        else:
            return ""

    @command(command="alts", params=[Const("setmain")], access_level="all",
             description="Set a new main",
             extended_description="You must run this from the character you want to be your new main")
    def alts_setmain_cmd(self, request, _):
        msg, result = self.alts_service.set_as_main(request.sender.char_id)

        if result:
            return f"<highlight>{request.sender.name}</highlight> character has been set as your main."
        elif msg == "not_an_alt":
            return "Error! This character cannot be set as your main since you do not have any alts."
        elif msg == "already_main":
            return "Error! This character is already set as your main."
        else:
            raise Exception("Unknown msg: " + msg)

    @command(command="alts", params=[Const("add"), Multiple(Character("character"))], access_level="all",
             description="Add an alt")
    def alts_add_cmd(self, request, _, alt_chars):
        responses = []
        for alt_char in alt_chars:
            if not alt_char.char_id:
                responses.append(StandardMessage.char_not_found(alt_char.name))
            elif alt_char.char_id == request.sender.char_id:
                responses.append("Error! You cannot register yourself as an alt.")
            else:
                msg, result = self.alts_service.add_alt(request.sender.char_id, alt_char.char_id)
                if result:
                    self.bot.send_private_message(alt_char.char_id,
                                                  f"<highlight>{request.sender.name}</highlight> has added you as an alt.",
                                                  conn=request.conn)
                    responses.append(f"<highlight>{alt_char.name}</highlight> has been added as your alt.")
                elif msg == "another_main":
                    responses.append(f"Error! <highlight>{alt_char.name}</highlight> already has alts.")
                else:
                    raise Exception("Unknown msg: " + msg)

        return "\n".join(responses)

    @command(command="alts", params=[Options(["rem", "remove"]), Character("character")], access_level="all",
             description="Remove an alt")
    def alts_remove_cmd(self, request, _, alt_char):
        if not alt_char.char_id:
            return StandardMessage.char_not_found(alt_char.name)

        msg, result = self.alts_service.remove_alt(request.sender.char_id, alt_char.char_id)
        if result:
            return f"<highlight>{alt_char.name}</highlight> has been removed as your alt."
        elif msg == "not_alt":
            return f"Error! <highlight>{alt_char.name}</highlight> is not your alt."
        elif msg == "remove_main":
            return "Error! You cannot remove your main."
        else:
            raise Exception("Unknown msg: " + msg)

    @command(command="alts", params=[Character("character")], access_level="member",
             description="Show alts of another character", sub_command="show")
    def alts_list_other_cmd(self, request, char):
        if not char.char_id:
            return StandardMessage.char_not_found(char.name)

        alts = self.alts_service.get_alts(char.char_id)
        blob = self.format_alt_list(alts)

        return ChatBlob(f"Alts of {alts[0].name} ({len(alts)})", blob)

    @command(command="altadmin", params=[Const("add"), Character("main"), Character("alt")],
             access_level="moderator",
             description="Add alts to main")
    def altadmin_add_cmd(self, request, _, main, alt):
        if not main.char_id:
            return StandardMessage.char_not_found(main.name)
        if not alt.char_id:
            return StandardMessage.char_not_found(alt.name)

        elif main.char_id == alt.char_id:
            return "Error! Alt and main are identical."

        msg, result = self.alts_service.add_alt(main.char_id, alt.char_id)
        if result:
            return f"The character <highlight>{alt.name}</highlight> was added as an alt of <highlight>{main.name}</highlight> successfully."
        elif msg == "another_main":
            return f"Error! <highlight>{alt.name}</highlight> already has alts."
        else:
            raise Exception("Unknown msg: " + msg)

    @command(command="altadmin", params=[Options(["rem", "remove"]), Character("main"), Character("alt")],
             access_level="moderator",
             description="Remove alts from main")
    def altadmin_remove_cmd(self, request, _, main, alt):
        if not main.char_id:
            return StandardMessage.char_not_found(main.name)
        if not alt.char_id:
            return StandardMessage.char_not_found(alt.name)

        msg, result = self.alts_service.remove_alt(main.char_id, alt.char_id)

        if result:
            return f"The character <highlight>{alt.name}</highlight> was added as an alt of <highlight>{main.name}</highlight> successfully."
        elif msg == "not_alt":
            return f"Error! <highlight>{alt.name}</highlight> is not an alt of <highlight>{main.name}</highlight>."
        elif msg == "remove_main":
            return "Error! Main characters may not be removed from their alt list."
        else:
            raise Exception("Unknown msg: " + msg)

    def format_alt_list(self, alts):
        blob = ""
        for alt in alts:

            blob += "<highlight>%s</highlight> (%d/<green>%d</green>) %s %s" % (
                alt.name, alt.level, alt.ai_level, alt.faction, alt.profession)
            if self.buddy_service.is_online(alt.char_id):
                blob += " [<green>Online</green>]"
            blob += "\n"
        return blob
