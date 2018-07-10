from core.chat_blob import ChatBlob
from core.command_param_types import Any, Int
from core.decorators import instance, command
from core.text import Text


@instance()
class LeProcsController:
    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.items_controller = registry.get_instance("items_controller")

    @command(command="leprocs", params=[], access_level="all",
             description="Show a list of professions with LE procs")
    def leprocs_list_command(self, channel, sender, reply, args):
        data = self.db.query("SELECT DISTINCT profession FROM leprocs ORDER BY profession ASC")

        blob = ""
        for row in data:
            blob += "<pagebreak>%s\n" % self.text.make_chatcmd(row.profession, "/tell <myname> leprocs %s" % row.profession)

        blob += "\nProc info provided by Wolfbiter (RK1), Gatester (RK2), DrUrban"

        reply(ChatBlob("LE Procs", blob))

    @command(command="leprocs", params=[Any("profession")], access_level="all",
             description="Show LE proc information for a specific profession")
    def leprocs_show_command(self, channel, sender, reply, args):
        prof_name = args[0]
        profession = self.util.get_profession(prof_name)

        if not profession:
            reply("Could not find profession <highlight>%s<end>." % prof_name)
            return

        data = self.db.query("SELECT * FROM leprocs WHERE profession LIKE ? ORDER BY proc_type ASC, research_lvl DESC", [profession])
        proc_type = ""
        blob = ""
        for row in data:
            if proc_type != row.proc_type:
                proc_type = row.proc_type
                blob += "\n<highlight>%s<end>\n" % proc_type

            blob += "<pagebreak>[%d] %s <orange>%s<end> %s <green>%s<end>\n" % (row.research_lvl, row.name, row.modifiers, row.duration, row.proc_trigger)

        blob += "\n\nNote: Offensive procs have a 5% chance of firing every time you attack; Defensive procs have a 10% chance of firing every time something attacks you."
        blob += "\n\nProc info provided by Wolfbiter (RK1), Gatester (RK2)"

        reply(ChatBlob("%s LE Procs" % profession, blob))
