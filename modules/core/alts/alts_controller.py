from core.decorators import instance, command
from core.commands.param_types import Any, Const, Options
from core.chat_blob import ChatBlob


@instance()
class AltsController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.alts_manager = registry.get_instance("alts_manager")
        self.character_manager = registry.get_instance("character_manager")

    def start(self):
        pass

    @command(command="alts", params=[], access_level="all",
             description="Show your alts")
    def alts_list_cmd(self, channel, sender, reply, args):
        alts = self.alts_manager.get_alts(sender.char_id)
        blob = ""
        for alt in alts:
            blob += "<highlight>%s<end> (%d/<green>%d<end>) %s %s\n" % (alt.name, alt.level, alt.ai_level, alt.faction, alt.profession)

        reply(ChatBlob("Alts for %s (%d)" % (sender.name, len(alts)), blob))

    @command(command="alts", params=[Const("add"), Any("character")], access_level="all",
             description="Add an alt")
    def alts_add_cmd(self, channel, sender, reply, args):
        alt = args[1].capitalize()
        alt_char_id = self.character_manager.resolve_char_to_id(alt)

        if not alt_char_id:
            reply("Could not find character <highlight>%s<end>." % alt)
        elif self.alts_manager.add_alt(sender.char_id, alt_char_id):
            reply("<highlight>%s<end> added as alt successfully." % alt)
        else:
            reply("Could not add <highlight>%s<end> as alt." % alt)

    @command(command="alts", params=[Options(["rem", "remove"]), Any("character")], access_level="all",
             description="Remove an alt")
    def alts_remove_cmd(self, channel, sender, reply, args):
        alt = args[2].capitalize()
        alt_char_id = self.character_manager.resolve_char_to_id(alt)

        if not alt_char_id:
            reply("Could not find character <highlight>%s<end>." % alt)
        elif self.alts_manager.remove_alt(sender.char_id, alt_char_id):
            reply("<highlight>%s<end> removed as alt successfully." % alt)
        else:
            reply("Could not remove <highlight>%s<end> as alt." % alt)

    @command(command="alts", params=[Any("character")], access_level="all",
             description="Show alts of another character")
    def alts_list_other_cmd(self, channel, sender, reply, args):
        name = args[1].capitalize()
        char_id = self.character_manager.resolve_char_to_id(name)
        if not char_id:
            reply("Could not find character <highlight>%s<end>." % name)
            return

        alts = self.alts_manager.get_alts(char_id)
        blob = ""
        for alt in alts:
            blob += "<highlight>%s<end> (%d/<green>%d<end>) %s %s\n" % (alt.name, alt.level, alt.ai_level, alt.faction, alt.profession)

        reply(ChatBlob("Alts for %s (%d)" % (name, len(alts)), blob))
