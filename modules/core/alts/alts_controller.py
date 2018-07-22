from core.decorators import instance, command
from core.command_param_types import Any, Const, Options
from core.chat_blob import ChatBlob
from core.alts.alts_service import AltsService


@instance()
class AltsController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.alts_service = registry.get_instance("alts_service")
        self.character_service = registry.get_instance("character_service")

    def start(self):
        pass

    @command(command="alts", params=[], access_level="all",
             description="Show your alts")
    def alts_list_cmd(self, channel, sender, reply, args):
        alts = self.alts_service.get_alts(sender.char_id)
        blob = ""
        for alt in alts:
            blob += "<highlight>%s<end> (%d/<green>%d<end>) %s %s%s\n" % (alt.name, alt.level, alt.ai_level, alt.faction, alt.profession, self.get_alt_status(alt.status))

        reply(ChatBlob("Alts of %s (%d)" % (alts[0].name, len(alts)), blob))

    def get_alt_status(self, status):
        if status == AltsService.UNCONFIRMED:
            return " - [unconfirmed]"
        elif status == AltsService.CONFIRMED:
            return ""
        else:
            return " - [main]"

    @command(command="alts", params=[Const("add"), Any("character")], access_level="all",
             description="Add an alt")
    def alts_add_cmd(self, channel, sender, reply, args):
        alt_char_name = args[1].capitalize()
        alt_char_id = self.character_service.resolve_char_to_id(alt_char_name)

        if not alt_char_id:
            reply("Could not find character <highlight>%s<end>." % alt_char_name)
            return
        elif alt_char_id == sender.char_id:
            reply("You cannot register yourself as an alt.")
            return

        # for now, always add alts as confirmed
        msg, result = self.alts_service.add_alt(sender.char_id, alt_char_id, AltsService.CONFIRMED)
        if result:
            reply("<highlight>%s<end> has been added as your alt." % alt_char_name)
        elif msg == "another_main":
            reply("<highlight>%s<end> already has alts." % alt_char_name)
        else:
            raise Exception("Unknown msg: " + msg)

    @command(command="alts", params=[Options(["rem", "remove"]), Any("character")], access_level="all",
             description="Remove an alt")
    def alts_remove_cmd(self, channel, sender, reply, args):
        alt = args[1].capitalize()
        alt_char_id = self.character_service.resolve_char_to_id(alt)

        if not alt_char_id:
            reply("Could not find character <highlight>%s<end>." % alt)
            return

        msg, result = self.alts_service.remove_alt(sender.char_id, alt_char_id)
        if result:
            reply("<highlight>%s<end> has been removed as your alt." % alt)
        elif msg == "not_alt":
            reply("<highlight>%s<end> is not your alt." % alt)
        elif msg == "unconfirmed_sender":
            reply("You cannot remove alts from an unconfirmed alt.")
        elif msg == "remove_main":
            reply("You cannot remove your main.")
        else:
            raise Exception("Unknown msg: " + msg)

    @command(command="alts", params=[Any("character")], access_level="member",
             description="Show alts of another character", sub_command="show")
    def alts_list_other_cmd(self, channel, sender, reply, args):
        name = args[0].capitalize()
        char_id = self.character_service.resolve_char_to_id(name)
        if not char_id:
            reply("Could not find character <highlight>%s<end>." % name)
            return

        alts = self.alts_service.get_alts(char_id)
        blob = ""
        for alt in alts:
            blob += "<highlight>%s<end> (%d/<green>%d<end>) %s %s\n" % (alt.name, alt.level, alt.ai_level, alt.faction, alt.profession)

        reply(ChatBlob("Alts of %s (%d)" % (alts[0].name, len(alts)), blob))
