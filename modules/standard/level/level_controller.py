from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.db import DB
from core.command_param_types import Int
import math


@instance()
class LevelController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.text = registry.get_instance("text")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.db.load_sql_file(self.module_dir + "/" + "alien_level.sql")
        self.db.load_sql_file(self.module_dir + "/" + "level.sql")

        self.command_alias_service.add_alias("lvl", "level")
        self.command_alias_service.add_alias("pvp", "level")
        self.command_alias_service.add_alias("team", "level")
        self.command_alias_service.add_alias("missions", "mission")
        self.command_alias_service.add_alias("mish", "mission")
        self.command_alias_service.add_alias("ailevel", "axp")

    @command(command="level", params=[Int("level")], access_level="all",
             description="Show information about a character level")
    def level_cmd(self, request, level):
        row = self.get_level_info(level)

        if row:
            msg = "<white>L %d: Team %d-%d</white><highlight> | </highlight><cyan>PvP %d-%d</cyan><highlight> | </highlight><orange>Missions %s</orange><highlight> | </highlight><blue>%d token(s)</blue>" %\
                  (row.level, row.team_min, row.team_max, row.pvp_min, row.pvp_max, row.missions, row.tokens)
            return msg
        else:
            return "Level must be between <highlight>1</highlight> and <highlight>220</highlight>."

    @command(command="mission", params=[Int("mission_level")], access_level="all",
             description="Show what character levels can roll a specified mission level",
             extended_description="Updated mission levels provided by Lucier")
    def mission_cmd(self, request, level):
        if 1 <= level <= 250:
            levels = self.get_mission_levels(level)

            return "QL %d missions can be rolled from these levels: %s" % (level, " ".join(levels))
        else:
            return "Mission level must be between <highlight>1</highlight> and <highlight>250</highlight>."

    @command(command="xp", params=[Int("start_level"), Int("end_level", is_optional=True)], access_level="all",
             description="Show the amount of XP needed to reach a certain level")
    def xp_range_cmd(self, request, start_level, end_level):
        end_level = end_level or start_level + 1

        if start_level == end_level:
            return "Start level must be different than end level."

        if start_level > end_level:
            start_level, end_level = end_level, start_level

        if 1 <= start_level <= 220 and 1 <= end_level <= 220:
            if end_level <= 200:
                xp = self.db.query_single("SELECT SUM(xpsk) AS total_xp FROM level WHERE level >= ? AND level < ?", [start_level, end_level])
                needed = "<highlight>%s</highlight> XP" % self.util.format_number(xp.total_xp)
            elif start_level >= 200:
                sk = self.db.query_single("SELECT SUM(xpsk) AS total_sk FROM level WHERE level >= ? AND level < ?", [start_level, end_level])
                needed = "<highlight>%s</highlight> SK" % self.util.format_number(sk.total_sk)
            else:
                xp = self.db.query_single("SELECT SUM(xpsk) AS total_xp FROM level WHERE level >= ? AND level < 200", [start_level])
                sk = self.db.query_single("SELECT SUM(xpsk) AS total_sk FROM level WHERE level >= 200 AND level < ?", [end_level])
                needed = "<highlight>%s</highlight> XP and <highlight>%s</highlight> SK" % (self.util.format_number(xp.total_xp), self.util.format_number(sk.total_sk))

            return "From the beginning of level <highlight>%d</highlight> you need %s to reach level <highlight>%d</highlight>" % (start_level, needed, end_level)
        else:
            return "Level must be between <highlight>1</highlight> and <highlight>219</highlight>."

    @command(command="axp", params=[], access_level="all",
             description="Show information about alien levels")
    def axp_single_cmd(self, request):
        data = self.db.query("SELECT * FROM alien_level ORDER BY alien_level ASC")

        rows = []
        for row in data:
            rows.append([f"<green>{row.alien_level}</green>", self.util.format_number(row.axp),
                        f"<highlight>{row.defender_rank}</highlight>", f"Min Level: {row.min_level}"])

        display_table = self.text.pad_table(rows, " ")

        blob = ""
        for cols in display_table:
            blob += "  ".join(cols) + "\n"

        return ChatBlob("Alien Levels", blob)

    def get_level_info(self, level):
        return self.db.query_single("SELECT * FROM level WHERE level = ?", [level])

    def get_mission_levels(self, level):
        levels = []
        data = self.db.query("SELECT * FROM level")
        str_level = str(level)
        for row in data:
            if str_level in row.missions.split(","):
                levels.append(str(row.level))

        return levels

    def get_mission_levels2(self, level):
        mission_coefficients = [0.7001, 0.75, 0.8, 0.85, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 1.7913]
        mission_levels = set()
        for i in mission_coefficients:
            val = math.floor(level * i)
            if val < 1:
                val = 1
            elif val > 250:
                val = 250

            # I couldn't get 4 values to match with 1.3?
            if i == 1.3 and (level == 90 or level == 170 or level == 180 or level == 190):
                val = val - 1

            mission_levels.add(val)

        return ",".join(map(lambda x: str(x), sorted(mission_levels)))
