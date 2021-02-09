from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.command_param_types import Any, Int


@instance()
class PerksController:
    def __init__(self):
        self.grades = ["shiny", "bright", "faded"]

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")

    def start(self):
        self.db.load_sql_file(self.module_dir + "/" + "perks.sql")

    @command(command="perks", params=[Int("level"), Any("profession")], access_level="all",
             description="Show what perks are available for specified level and profession")
    def perks_cmd(self, request, level, profession):
        if level < 1 or level > 220:
            return "Level must be between <highlight>1</highlight> and <highlight>220</highlight>."

        prof = self.util.get_profession(profession)
        if not prof:
            return "Could not find profession <highlight>%s</highlight>" % profession

        sql = """
            SELECT
                p.name AS perk_name,
                MAX(pl.number) AS max_perk_level,
                SUM(plb.amount) AS buff_amount,
                plb.skill
            FROM
                perk p
                JOIN perk_prof pp ON p.id = pp.perk_id
                JOIN perk_level pl ON p.id = pl.perk_id
                JOIN perk_level_buffs plb ON pl.id = plb.perk_level_id
            WHERE
                pp.profession = ?
                AND pl.min_level <= ?
            GROUP BY
                p.name,
                plb.skill
            ORDER BY
                p.name"""

        data = self.db.query(sql, [prof, level])

        blob = ""
        current_perk = ""
        for row in data:
            if row.perk_name != current_perk:
                blob += "\n<header2>%s %s</header2>\n" % (row.perk_name, row.max_perk_level)
                current_perk = row.perk_name
            blob += "%s <highlight>%d</highlight>\n" % (row.skill, row.buff_amount)

        return ChatBlob("Buff Perks for %d %s" % (level, prof), blob)
