from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob
from core.command_param_types import Any, Options


@instance()
class WhatBuffsController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("buffs", "whatbuffs")

    @command(command="whatbuffs", params=[], access_level="all",
             description="Find items or nanos that buff a skill (or ability)")
    def whatbuffs_list_cmd(self, request):
        data = self.db.query("SELECT name FROM skills ORDER BY name ASC")
        blob = ""
        for row in data:
            blob += self.text.make_chatcmd(row.name, "/tell <myname> whatbuffs %s" % row.name) + "\n"

        blob += self.get_footer()
        return ChatBlob("Whatbuffs Skill List", blob)

    @command(command="whatbuffs", params=[
        Any("skill"),
        Options(["arms", "back", "chest", "deck", "feet", "fingers", "hands", "head", "hud", "legs", "nano", "neck", "shoulders", "unknown", "util", "weapon", "wrists"])],
             access_level="all", description="Find items or nanos that buff a skill (or ability)")
    def whatbuffs_detail_cmd(self, request, skill_name, item_type):
        item_type = item_type.capitalize()

        return self.show_search_results(item_type, skill_name)

    @command(command="whatbuffs", params=[Any("skill")], access_level="all",
             description="Find items or nanos that buff a skill (or ability)")
    def whatbuffs_skill_cmd(self, request, skill_name):
        skills = self.search_for_skill(skill_name)
        if len(skills) == 0:
            return "Could not find skill <highlight>%s<end>." % skill_name
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
            for row in data:
                blob += "%s (%d)\n" % (self.text.make_chatcmd(row.item_type, "/tell <myname> whatbuffs %s %s" % (skill.name, row.item_type)), row.cnt)

            blob += self.get_footer()
            return ChatBlob("Whatbuffs %s - Choose Type" % skill.name, blob)
        else:
            blob = "Choose a skill:\n\n"
            for skill in skills:
                blob += self.text.make_chatcmd(skill.name, "/tell <myname> whatbuffs %s" % skill.name) + "\n"

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
            return "Could not find skill <highlight>%s<end>." % skill_name
        elif len(skills) == 1:
            skill = skills.pop()
            return self.get_search_results(item_type, skill)
        else:
            blob = ""
            for skill in skills:
                blob += self.text.make_chatcmd(skill.name, "/tell <myname> whatbuffs %s %s" % (skill.name, item_type)) + "\n"

            return ChatBlob("Whatbuffs - Choose Skill", blob)

    def get_search_results(self, item_type, skill):
        data = self.db.query("SELECT aodb.*, b.amount "
                             "FROM aodb "
                             "JOIN item_types i ON aodb.highid = i.item_id "
                             "JOIN item_buffs b ON aodb.highid = b.item_id "
                             "JOIN skills s ON b.attribute_id = s.id "
                             "WHERE i.item_type LIKE ? AND s.id = ? "
                             "ORDER BY amount DESC", [item_type, skill.id])

        if len(data) == 0:
            return "No items found of type <highlight>%s<end> that buff <highlight>%s<end>." % (item_type, skill.name)
        else:
            blob = ""
            for row in data:
                blob += "%s (%d)\n" % (self.text.make_item(row.lowid, row.highid, row.highql, row.name), row.amount)

            blob += self.get_footer()

            return ChatBlob("Whatbuffs - %s %s (%d)" % (item_type, skill.name, len(data)), blob)

    def get_footer(self):
        return "\nItem DB Extraction Info provided by Unk"
