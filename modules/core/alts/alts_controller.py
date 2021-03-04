import hjson

from core.alts_service import AltsService
from core.chat_blob import ChatBlob
from core.command_param_types import Const, Options, Character, Multiple
from core.decorators import instance, command
from core.translation_service import TranslationService


@instance()
class AltsController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.alts_service: AltsService = registry.get_instance("alts_service")
        self.buddy_service = registry.get_instance("buddy_service")
        self.util = registry.get_instance("util")
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.getresp = self.ts.get_response

    def start(self):
        self.ts.register_translation("module/alts", self.load_alts_msg)

    def load_alts_msg(self):
        with open("modules/core/alts/alts.msg", mode="r", encoding="UTF-8") as f:
            return hjson.load(f)

    @command(command="alts", params=[], access_level="all",
             description="Show your alts")
    def alts_list_cmd(self, request):
        alts = self.alts_service.get_alts(request.sender.char_id)
        blob = self.format_alt_list(alts)

        return ChatBlob(self.getresp("module/alts", "list", {"char": alts[0].name, "amount": len(alts)}), blob)

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
            return self.getresp("module/alts", "new_main", {"char": request.sender.name})
        elif msg == "not_an_alt":
            return self.getresp("module/alts", "not_an_alt")
        elif msg == "already_main":
            return self.getresp("module/alts", "already_main")
        else:
            raise Exception("Unknown msg: " + msg)

    @command(command="alts", params=[Const("add"), Multiple(Character("character"))], access_level="all",
             description="Add an alt")
    def alts_add_cmd(self, request, _, alt_chars):
        responses = []
        for alt_char in alt_chars:
            if not alt_char.char_id:
                responses.append(self.getresp("global", "char_not_found", {"char": alt_char.name}))
            elif alt_char.char_id == request.sender.char_id:
                responses.append(self.getresp("module/alts", "add_fail_self"))
            else:
                msg, result = self.alts_service.add_alt(request.sender.char_id, alt_char.char_id)
                if result:
                    self.bot.send_private_message(alt_char.char_id,
                                                  self.getresp("module/alts", "add_success_target", {"char": request.sender.name}),
                                                  conn=request.conn)
                    responses.append(self.getresp("module/alts", "add_success_self", {"char": alt_char.name}))
                elif msg == "another_main":
                    responses.append(self.getresp("module/alts", "add_fail_already", {"char": alt_char.name}))
                else:
                    raise Exception("Unknown msg: " + msg)

        return "\n".join(responses)

    @command(command="alts", params=[Options(["rem", "remove"]), Character("character")], access_level="all",
             description="Remove an alt")
    def alts_remove_cmd(self, request, _, alt_char):
        if not alt_char.char_id:
            return self.getresp("global", "char_not_found", {"char": alt_char.name})

        msg, result = self.alts_service.remove_alt(request.sender.char_id, alt_char.char_id)
        if result:
            return self.getresp("module/alts", "rem_success", {"char": alt_char.name})
        elif msg == "not_alt":
            return self.getresp("module/alts", "rem_fail_not", {"char": alt_char.name})
        elif msg == "remove_main":
            return self.getresp("module/alts", "rem_fail_main")
        else:
            raise Exception("Unknown msg: " + msg)

    @command(command="alts", params=[Character("character")], access_level="member",
             description="Show alts of another character", sub_command="show")
    def alts_list_other_cmd(self, request, char):
        if not char.char_id:
            return self.getresp("global", "char_not_found", {"char": char.name})

        alts = self.alts_service.get_alts(char.char_id)
        blob = self.format_alt_list(alts)

        return ChatBlob(self.getresp("module/alts", "list", {"char": alts[0].name, "amount": len(alts)}), blob)

    @command(command="altadmin", params=[Const("add"), Character("main"), Character("alt")],
             access_level="admin",
             description="Add alts to Main")
    def altadmin_add_cmd(self, request, _, main, alt):
        if not main.char_id:
            return self.getresp("global", "char_not_found", {"char": main.name})
        if not alt.char_id:
            return self.getresp("global", "char_not_found", {"char": alt.name})

        elif main.char_id == alt.char_id:
            return self.getresp("module/alts", "altadmin_add_same")

        msg, result = self.alts_service.add_alt(main.char_id, alt.char_id)
        if result:
            return self.getresp("module/alts", "altadmin_add_success",
                                {"alt": alt.name,
                                 "main": main.name})
        elif msg == "another_main":
            return self.getresp("module/alts", "add_fail_already", {"char": alt.name})
        else:
            raise Exception("Unknown msg: " + msg)

    @command(command="altadmin", params=[Options(["rem", "remove"]), Character("main"), Character("alt")],
             access_level="admin",
             description="Remove alts of main")
    def altadmin_remove_cmd(self, request, _, main, alt):
        if not main.char_id:
            return self.getresp("global", "char_not_found", {"char": main.name})
        if not alt.char_id:
            return self.getresp("global", "char_not_found", {"char": alt.name})

        msg, result = self.alts_service.remove_alt(main.char_id, alt.char_id)

        if result:
            return self.getresp("module/alts", "altadmin_rem_success", {"alt": alt.name, "main": main.name})
        elif msg == "not_alt":
            return self.getresp("module/alts", "altadmin_rem_fail_not", {"alt": alt.name, "main": main.name})
        elif msg == "remove_main":
            return self.getresp("module/alts", "altadmin_rem_fail_main")
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
