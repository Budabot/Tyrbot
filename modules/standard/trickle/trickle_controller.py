from core.decorators import instance, command
from core.db import DB
from core.dict_object import DictObject
from core.text import Text
from core.chat_blob import ChatBlob
from core.command_param_types import Any, CommandParam
import re


class TrickleParam(CommandParam):
    def __init__(self):
        super().__init__()
        self.ability_first = re.compile(r"\s+([a-z]+)\s+([0-9]+)")
        self.amount_first = re.compile(r"\s+([0-9]+)\s+([a-z]+)")

    def get_regex(self):
        regex = r"((\s+[a-z]+\s+[0-9]+|\s+[0-9]+\s+[a-z]+)+)"
        return regex

    def get_name(self):
        return "<highlight>ability</highlight> <highlight>amount</highlight>"

    def process_matches(self, params):
        i = params.pop(0)
        matches_amount_first = self.amount_first.findall(i)
        matches_ability_first = self.ability_first.findall(i)
        params.pop(0)

        result = []
        if len(matches_amount_first) > len(matches_ability_first):
            for match in matches_amount_first:
                result.append(DictObject({
                    "ability": match[1],
                    "amount": int(match[0])
                }))
        else:
            for match in matches_ability_first:
                result.append(DictObject({
                    "ability": match[0],
                    "amount": int(match[1])
                }))

        return result


@instance()
class TrickleController:
    def __init__(self):
        self.ability_first = re.compile(" ([a-z]+) ([0-9]+)")
        self.amount_first = re.compile(" ([0-9]+) ([a-z]+)")

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.util = registry.get_instance("util")

    @command(command="trickle", params=[TrickleParam()], access_level="all",
             description="Show skill increases due to trickle")
    def trickle_ability_cmd(self, request, trickle_params):
        abilities_map = {}

        # initialize map with 0s
        for ability in self.util.get_all_abilities():
            abilities_map[ability] = 0

        for p in trickle_params:
            ability = self.util.get_ability(p.ability)
            if not ability:
                return "Unknown ability <highlight>%s</highlight>." % p.ability

            abilities_map[ability] = p.amount

        trickle_amounts = self.get_trickle_amounts(abilities_map)
        return self.format_trickle_output(abilities_map, trickle_amounts)

    @command(command="trickle", params=[Any("skill")], access_level="all",
             description="Show how much ability is needed to trickle a skill")
    def trickle_skill_cmd(self, request, search):
        data = self.db.query("SELECT * FROM trickle WHERE name <EXTENDED_LIKE=0> ?", [search], extended_like=True)
        count = len(data)

        if count == 0:
            return "Could not find any skills for <highlight>%s</highlight>." % search
        elif count == 1:
            row = data[0]
            return self.format_trickle_amounts(row)
        else:
            blob = ""
            for row in data:
                blob += self.format_trickle_amounts(row) + "\n"
            return ChatBlob("Trickle Info for <highlight>%s</highlight>" % search, blob)

    def format_trickle_amounts(self, row):
        msg = "<highlight>%s</highlight> " % row.name
        for ability in self.util.get_all_abilities():
            amount = row["amount_" + ability.lower()]
            if amount > 0:
                value = 4 / amount
                msg += "(%s: %s) " % (ability, round(value, 2))
        return msg

    def get_abilities_map(self, search, is_reversed):
        if is_reversed:
            matches = self.amount_first.findall(search)
        else:
            matches = self.ability_first.findall(search)

        m = {}

        # initialize map with 0s
        for ability in self.util.get_all_abilities():
            m[ability] = 0

        # add values that for abilities that were passed in
        for val in matches:
            if is_reversed:
                ability = self.util.get_ability(val[1])
                amount = int(val[0])
            else:
                ability = self.util.get_ability(val[0])
                amount = int(val[1])
            m[ability] += amount

        return m

    def get_trickle_amounts(self, abilities_map):
        sql = """
            SELECT
                group_name,
                name,
                amount_agility,
                amount_intelligence,
                amount_psychic,
                amount_stamina,
                amount_strength,
                amount_sense,
                (amount_agility * %d
                    + amount_intelligence * %d
                    + amount_psychic * %d
                    + amount_stamina * %d
                    + amount_strength * %d
                    + amount_sense * %d) AS amount
            FROM
                trickle
            GROUP BY
                group_name,
                name,
                amount_agility,
                amount_intelligence,
                amount_psychic,
                amount_stamina,
                amount_strength,
                amount_sense
            HAVING
                amount > 0
            ORDER BY
                id""" % \
              (abilities_map["Agility"], abilities_map["Intelligence"], abilities_map["Psychic"], abilities_map["Stamina"], abilities_map["Strength"], abilities_map["Sense"])

        return self.db.query(sql)

    def format_trickle_output(self, abilities_map, trickle_amounts):
        # create blob
        blob = ""
        group_name = ""
        for row in trickle_amounts:
            if row.group_name != group_name:
                blob += "\n<header2>%s<end>\n" % row.group_name
                group_name = row.group_name

            blob += "%s <highlight>%g</highlight>\n" % (row.name, row.amount / 4)

        # create title
        title = "Trickle Results: " + ", ".join(map(lambda x: "%s <highlight>%d</highlight>" % (x[0], x[1]), filter(lambda x: x[1] > 0, abilities_map.items())))

        return ChatBlob(title, blob)
