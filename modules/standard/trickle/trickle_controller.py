from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob
from core.command_param_types import Int, Any, Regex
import os
import re


@instance()
class TrickleController:
    def __init__(self):
        self.ability_first = re.compile(" ([a-z]+) ([0-9]+)")
        self.amount_first = re.compile(" ([0-9]+) ([a-z]+)")

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.util = registry.get_instance("util")

    def start(self):
        pass

    @command(command="trickle", params=[Regex("ability amount", "(( ([a-z]+) ([0-9]+))+)")], access_level="all",
             description="Show skill increases due to trickle")
    def trickle_ability_cmd1(self, channel, sender, reply, args):
        abilities_map = self.get_abilities_map(args[0][0], False)
        trickle_amounts = self.get_trickle_amounts(abilities_map)
        reply(self.format_trickle_output(abilities_map, trickle_amounts))

    @command(command="trickle", params=[Regex("amount ability", "(( ([0-9]+) ([a-z]+))+)")], access_level="all",
             description="Show skill increases due to trickle")
    def trickle_ability_cmd2(self, channel, sender, reply, args):
        abilities_map = self.get_abilities_map(args[0][0], True)
        trickle_amounts = self.get_trickle_amounts(abilities_map)
        reply(self.format_trickle_output(abilities_map, trickle_amounts))

    @command(command="trickle", params=[Any("skill")], access_level="all",
             description="Show how much ability is needed to trickle a skill")
    def trickle_skill_cmd(self, channel, sender, reply, args):
        search = args[0]

        data = self.db.query(*self.db.handle_extended_like("SELECT * FROM trickle WHERE name <EXTENDED_LIKE=0> ?", [search]))
        count = len(data)

        if count == 0:
            reply("Could not find any skills for <highlight>%s<end>." % search)
        elif count == 1:
            row = data[0]
            reply(self.format_trickle_amounts(row))
        else:
            blob = ""
            for row in data:
                blob += self.format_trickle_amounts(row) + "\n"
            reply(ChatBlob("Trickle Info for <highlight>%s<end>" % search, blob))

    def format_trickle_amounts(self, row):
        msg = "<highlight>%s<end> " % row.name
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

            blob += "%s <highlight>%g<end>\n" % (row.name, row.amount / 4)

        # create title
        title = "Trickle Results: " + ", ".join(map(lambda x: "%s <highlight>%d<end>" % (x[0], x[1]), filter(lambda x: x[1] > 0, abilities_map.items())))

        return ChatBlob(title, blob)
