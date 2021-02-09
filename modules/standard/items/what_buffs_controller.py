from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob
from core.command_param_types import Any, Options, Const


@instance()
class WhatBuffsController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def pre_start(self):
        self.db.load_sql_file(self.module_dir + "/" + "item_buffs.sql")
        self.db.load_sql_file(self.module_dir + "/" + "item_types.sql")
        self.db.load_sql_file(self.module_dir + "/" + "skills.sql")

    def start(self):
        self.command_alias_service.add_alias("buffs", "whatbuffs")

    @command(command="whatbuffs", params=[], access_level="all",
             description="Find items or nanos that buff a skill (or ability)")
    def whatbuffs_list_cmd(self, request):
        data = self.db.query("SELECT name FROM skills ORDER BY name ASC")
        blob = ""
        for row in data:
            blob += self.text.make_tellcmd(row.name, "whatbuffs %s" % row.name) + "\n"

        blob += self.get_footer()
        return ChatBlob("Whatbuffs Skill List", blob)

    @command(command="whatbuffs", params=[
        Any("skill"),
        Options(["arms", "back", "chest", "deck", "feet", "fingers", "hands", "head", "hud", "legs", "nanoprogram", "neck", "shoulders", "unknown", "util", "weapon", "wrists", "all"])],
             access_level="all", description="Find items or nanos that buff a skill (or ability) for a particular item type")
    def whatbuffs_detail_cmd(self, request, skill_name, item_type):
        item_type = item_type.capitalize()

        return self.show_search_results(item_type, skill_name)

    @command(command="whatbuffs", params=[Any("skill")], access_level="all",
             description="Find items or nanos that buff a skill (or ability)")
    def whatbuffs_skill_cmd(self, request, skill_name):
        skills = self.search_for_skill(skill_name)
        if len(skills) == 0:
            return "Could not find skill <highlight>%s</highlight>." % skill_name
        elif len(skills) == 1:
            skill = skills.pop()

            data = self.db.query("SELECT i.item_type, COUNT(1) AS cnt "
                                 "FROM aodb "
                                 "JOIN item_types i ON aodb.highid = i.item_id "
                                 "JOIN item_buffs b ON aodb.highid = b.item_id "
                                 "JOIN skills s ON b.attribute_id = s.id "
                                 "WHERE s.id = ? "
                                 "GROUP BY item_type "
                                 "HAVING cnt > 0 "
                                 "ORDER BY item_type ASC", [skill.id])

            blob = ""
            total_count = 0
            for row in data:
                blob += "%s (%d)\n" % (self.text.make_tellcmd(row.item_type, "whatbuffs %s %s" % (skill.name, row.item_type)), row.cnt)
                total_count += row.cnt
            blob += "\n%s (%d)\n" % (self.text.make_tellcmd("All", "whatbuffs %s %s" % (skill.name, "All")), total_count)

            blob += self.get_footer()
            return ChatBlob("Whatbuffs %s - Choose Type" % skill.name, blob)
        else:
            blob = "Choose a skill:\n\n"
            for skill in skills:
                blob += self.text.make_tellcmd(skill.name, "whatbuffs %s" % skill.name) + "\n"

            blob += self.get_footer()
            return ChatBlob("Whatbuffs - Choose Skill", blob)

    def search_for_skill(self, skill_name):
        skill_name = skill_name.lower()

        data = self.db.query("SELECT id, name FROM skills WHERE name <EXTENDED_LIKE=0> ? OR common_name <EXTENDED_LIKE=1> ?", [skill_name, skill_name], extended_like=True)

        # check for exact match first, in order to disambiguate between Bow and Bot Special Attack
        for row in data:
            if row.name.lower() == skill_name:
                return [row]

        return data

    def show_search_results(self, item_type, skill_name):
        skills = self.search_for_skill(skill_name)

        if len(skills) == 0:
            return "Could not find skill <highlight>%s</highlight>." % skill_name
        elif len(skills) == 1:
            skill = skills.pop()
            return self.get_search_results(item_type, skill)
        else:
            blob = ""
            for skill in skills:
                blob += self.text.make_tellcmd(skill.name, "whatbuffs %s %s" % (skill.name, item_type)) + "\n"

            return ChatBlob("Whatbuffs - Choose Skill", blob)

    def get_search_results(self, item_type, skill):
        data = self.db.query("SELECT aodb.*, b.amount, i.item_type "
                             "FROM aodb "
                             "JOIN item_types i ON aodb.highid = i.item_id "
                             "JOIN item_buffs b ON aodb.highid = b.item_id "
                             "JOIN skills s ON b.attribute_id = s.id "
                             "WHERE i.item_type LIKE ? AND s.id = ? "
                             "ORDER BY item_type, amount DESC", ["%" if item_type == "All" else item_type, skill.id])

        if len(data) == 0:
            return "No items found of type <highlight>%s</highlight> that buff <highlight>%s</highlight>." % (item_type, skill.name)
        else:
            current_item_type = ""
            blob = ""
            for row in data:
                if current_item_type != row.item_type:
                    blob += "\n\n<header2>%s</header2>\n" % row.item_type
                    current_item_type = row.item_type

                blob += "%s (%d)\n" % (self.text.make_item(row.lowid, row.highid, row.highql, row.name), row.amount)

            blob += self.get_footer()

            return ChatBlob("Whatbuffs - %s %s (%d)" % (skill.name, item_type, len(data)), blob)

    def get_footer(self):
        return "\nItem DB Extraction Info provided by Unk"
