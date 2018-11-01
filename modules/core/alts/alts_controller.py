from core.decorators import instance, command
from core.command_param_types import Any, Const, Options, Character
from core.chat_blob import ChatBlob
from core.alts.alts_service import AltsService


@instance()
class AltsController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.alts_service = registry.get_instance("alts_service")
        self.buddy_service = registry.get_instance("buddy_service")

    @command(command="alts", params=[], access_level="all",
             description="Show your alts")
    def alts_list_cmd(self, request):
        alts = self.alts_service.get_alts(request.sender.char_id)
        blob = self.format_alt_list(alts)

        return ChatBlob("Alts of %s (%d)" % (alts[0].name, len(alts)), blob)

    def get_alt_status(self, status):
        if status == AltsService.MAIN:
            return " - [main]"
        else:
            return ""

    @command(command="alts", params=[Const("setmain")], access_level="member", sub_command="show",
             description="Set a new main", extended_description="You must run this from the character you want to be your new main")
    def alts_setmain_cmd(self, request, char):
        msg, result = self.alts_service.set_as_main(request.sender.char_id)

        if result:
            return "This character has been set as your main."
        elif msg == "not_an_alt":
            return "Error! This character cannot be set as your main since you do not have any alts."
        elif msg == "already_main":
            return "Error! This character is already set as your main."
        else:
            raise Exception("Unknown msg: " + msg)

    @command(command="alts", params=[Const("add"), Character("character")], access_level="all",
             description="Add an alt")
    def alts_add_cmd(self, request, _, alt_char):
        if not alt_char.char_id:
            return "Error! Could not find character <highlight>%s<end>." % alt_char.name
        elif alt_char.char_id == request.sender.char_id:
            return "Error! You cannot register yourself as an alt."

        msg, result = self.alts_service.add_alt(request.sender.char_id, alt_char.char_id)
        if result:
            self.bot.send_private_message(alt_char.char_id, "<highlight>%s<end> has added you as an alt." % request.sender.name)
            return "<highlight>%s<end> has been added as your alt." % alt_char.name
        elif msg == "another_main":
            return "Error! <highlight>%s<end> already has alts." % alt_char.name
        else:
            raise Exception("Unknown msg: " + msg)

    @command(command="alts", params=[Options(["rem", "remove"]), Character("character")], access_level="all",
             description="Remove an alt")
    def alts_remove_cmd(self, request, _, alt_char):
        if not alt_char.char_id:
            return "Error! Could not find character <highlight>%s<end>." % alt_char.name

        msg, result = self.alts_service.remove_alt(request.sender.char_id, alt_char.char_id)
        if result:
            return "<highlight>%s<end> has been removed as your alt." % alt_char.name
        elif msg == "not_alt":
            return "Error! <highlight>%s<end> is not your alt." % alt_char.name
        elif msg == "remove_main":
            return "Error! You cannot remove your main."
        else:
            raise Exception("Unknown msg: " + msg)

    @command(command="alts", params=[Character("character")], access_level="member",
             description="Show alts of another character", sub_command="show")
    def alts_list_other_cmd(self, request, char):
        if not char.char_id:
            return "Error! Could not find character <highlight>%s<end>." % char.name

        alts = self.alts_service.get_alts(char.char_id)
        blob = self.format_alt_list(alts)

        return ChatBlob("Alts of %s (%d)" % (alts[0].name, len(alts)), blob)

    def format_alt_list(self, alts):
        blob = ""
        for alt in alts:
            blob += "<highlight>%s<end> (%d/<green>%d<end>) %s %s" % (alt.name, alt.level, alt.ai_level, alt.faction, alt.profession)
            if self.buddy_service.is_online(alt.char_id):
                blob += " [<green>Online<end>]"
            blob += "\n"
        return blob
