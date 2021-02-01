from core.chat_blob import ChatBlob
from core.command_param_types import Any
from core.decorators import instance, command
from core.text import Text


@instance()
class LeProcsController:
    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("leproc", "leprocs")

    @command(command="leprocs", params=[], access_level="all",
             description="Show a list of professions with LE procs")
    def leprocs_list_command(self, request):
        data = self.db.query("SELECT DISTINCT profession FROM leprocs ORDER BY profession ASC")

        blob = ""
        for row in data:
            blob += "<pagebreak>%s\n" % self.text.make_tellcmd(row.profession, "leprocs %s" % row.profession)

        blob += "\nProc info provided by Wolfbiter (RK1), Gatester (RK2), DrUrban"

        return ChatBlob("LE Procs", blob)

    @command(command="leprocs", params=[Any("profession")], access_level="all",
             description="Show LE proc information for a specific profession")
    def leprocs_show_command(self, request, prof_name):
        profession = self.util.get_profession(prof_name)

        if not profession:
            return "Could not find profession <highlight>%s</highlight>." % prof_name

        data = self.db.query("SELECT * FROM leprocs WHERE profession LIKE ? ORDER BY proc_type ASC, research_lvl DESC", [profession])
        proc_type = ""
        blob = ""
        for row in data:
            if proc_type != row.proc_type:
                proc_type = row.proc_type
                blob += "\n<highlight>%s</highlight>\n" % proc_type

            blob += "<pagebreak>[%d] %s <orange>%s</orange> %s <green>%s</green>\n" % (row.research_lvl, row.name, row.modifiers, row.duration, row.proc_trigger)

        blob += "\n\nNote: Offensive procs have a 5% chance of firing every time you attack; Defensive procs have a 10% chance of firing every time something attacks you."
        blob += "\n\nProc info provided by Wolfbiter (RK1), Gatester (RK2)"

        return ChatBlob("%s LE Procs" % profession, blob)
