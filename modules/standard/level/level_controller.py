from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.command_param_types import Int


@instance()
class LevelController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")

    @command(command="level", params=[Int("level")], access_level="all",
             description="Show information about a character level", aliases=["i"])
    def level_cmd(self, channel, sender, reply, args):
        level = args[0]
        row = self.get_level_info(level)

        if level:
            msg = "<white>L %d: Team %d-%d<end><highlight> | <end><cyan>PvP %d-%d<end><highlight> | <end><orange>Missions %s<end><highlight> | <end><blue>%d token(s)<end>" %\
                  (row.level, row.team_min, row.team_max, row.pvp_min, row.pvp_max, row.missions, row.tokens)
            reply(msg)
        else:
            reply("Level must be between <highlight>1<end> and <highlight>220<end>.")

    def get_level_info(self, level):
        return self.db.query_single("SELECT * FROM level WHERE level = ?", [level])
