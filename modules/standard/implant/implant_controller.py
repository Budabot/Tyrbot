import math

from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.command_param_types import Any, Const, Int
from core.dict_object import DictObject


@instance()
class ImplantController:
    def __init__(self):
        self.grades = ["shiny", "bright", "faded"]

        self.normal_ability_req = {1: 6, 200: 404, 201: 426, 300: 1095}
        self.normal_treatment_req = {1: 11, 200: 951, 201: 1001, 300: 2051}

        self.jobe_ability_req = {1: 6, 200: 464, 201: 476, 300: 1231}
        self.jobe_treatment_req = {1: 11, 200: 1005, 201: 1001, 300: 2051}

        self.ability_shiny_bonus = {1: 5, 200: 55, 201: 55, 300: 73}
        self.ability_bright_bonus = {1: 3, 200: 33, 201: 33, 300: 44}
        self.ability_faded_bonus = {1: 2, 200: 22, 201: 22, 300: 29}

        self.skill_shiny_bonus = {1: 6, 200: 105, 201: 106, 300: 141}
        self.skill_bright_bonus = {1: 3, 200: 63, 201: 63, 300: 85}
        self.skill_faded_bonus = {1: 2, 200: 42, 201: 42, 300: 57}

        self.normal_build_shiny = {1: 4, 200: 800, 201: 994, 300: 1575}
        self.normal_build_bright = {1: 3, 200: 600, 201: 753, 300: 1125}
        self.normal_build_faded = {1: 2, 200: 400, 201: 552, 300: 825}

        self.jobe_build_shiny = {1: 6, 200: 1250, 201: 1356, 300: 2025}
        self.jobe_build_bright = {1: 4, 200: 950, 201: 1055, 300: 1575}
        self.jobe_build_faded = {1: 3, 200: 650, 201: 753, 300: 1125}

        self.clean_np = {1: 1, 200: 200}
        self.clean_be = {1: 4, 200: 950}

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.text = registry.get_instance("text")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.db.load_sql_file(self.module_dir + "/sql/" + "Ability.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "Cluster.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "ClusterImplantMap.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "ClusterType.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "EffectTypeMatrix.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "EffectValue.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "ImplantMatrix.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "ImplantType.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "Profession.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "Symbiant.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "SymbiantAbilityMatrix.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "SymbiantClusterMatrix.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "SymbiantProfessionMatrix.sql")

        self.db.load_sql_file(self.module_dir + "/sql/" + "implant_requirements.sql")

        self.command_alias_service.add_alias("implants", "implant")

    @command(command="implant", params=[Int("ql")], access_level="all",
             description="Shows information about an implant at given QL")
    def implant_cmd(self, request, ql):
        if ql > 300 or ql < 1:
            return "Implant QL must be between <highlight>1</highlight> and <highlight>300</highlight>."

        implant = self.get_implant_by_ql(ql)
        blob = self.format_implant(implant)

        return ChatBlob(f"Implant QL {implant.ql} ({implant.ability} Ability, {implant.treatment} Treatment)", blob)

    @command(command="implant", params=[Int("ability"), Int("treatment")], access_level="all",
             description="Shows highest QL implant for a given ability and treatment")
    def implant_requirement_cmd(self, request, ability, treatment):
        implant = self.get_implant_by_requirements(ability, treatment)
        if not implant:
            return "You do not have enough ability or treatment to wear an implant."

        blob = self.format_implant(implant)

        return ChatBlob(f"Implant QL {implant.ql} ({implant.ability} Ability, {implant.treatment} Treatment)", blob)

    def get_implant_by_requirements(self, ability, treatment):
        row = self.db.query_single("SELECT ql FROM implant_requirement WHERE ability <= ? AND treatment <= ? ORDER BY ql DESC LIMIT 1",
                                   [ability, treatment])

        if row:
            return self.get_implant_by_ql(row.ql)
        else:
            return None

    def format_implant(self, implant):
        blob = "<header2>Requirements to Wear</header2>\n"
        blob += "<highlight>%d</highlight> Treatment\n" % implant.treatment
        blob += "<highlight>%d</highlight> Ability\n" % implant.ability

        blob += "\n<header2>Ability Cluster Bonuses</header2>\n"
        blob += "<highlight>%d</highlight> Shiny (%d - %d)\n" % (implant.ability_shiny, implant.ability_shiny_min, implant.ability_shiny_max)
        blob += "<highlight>%d</highlight> Bright (%d - %d)\n" % (implant.ability_bright, implant.ability_bright_min, implant.ability_bright_max)
        blob += "<highlight>%d</highlight> Faded (%d - %d)\n" % (implant.ability_faded, implant.ability_faded_min, implant.ability_faded_max)

        blob += "\n<header2>Skill Cluster Bonuses</header2>\n"
        blob += "<highlight>%d</highlight> Shiny (%d - %d)\n" % (implant.skill_shiny, implant.skill_shiny_min, implant.skill_shiny_max)
        blob += "<highlight>%d</highlight> Bright (%d - %d)\n" % (implant.skill_bright, implant.skill_bright_min, implant.skill_bright_max)
        blob += "<highlight>%d</highlight> Faded (%d - %d)\n" % (implant.skill_faded, implant.skill_faded_min, implant.skill_faded_max)

        blob += "\n<header2>Requirements to Clean</header2>\n"
        if implant.ql <= 200:
            blob += "<highlight>%d</highlight> Break&Entry\n" % implant.clean_break_and_entry
            blob += "<highlight>%d</highlight> NanoProgramming\n" % implant.clean_nano_programming
        else:
            blob += "Refined implants cannot be cleaned\n"

        blob += "\n<header2>Max Requirements to Build</header2> (actual requirements may be lower)\n"
        blob += "<highlight>%d</highlight> NanoProgramming for Shiny\n" % implant.build_shiny
        blob += "<highlight>%d</highlight> NanoProgramming for Bright\n" % implant.build_bright
        blob += "<highlight>%d</highlight> NanoProgramming for Faded\n" % implant.build_faded

        blob += "\n<header2>Min Cluster QL</header2>\n"
        blob += "<highlight>%d</highlight> Shiny\n" % implant.minimum_cluster_shiny
        blob += "<highlight>%d</highlight> Bright\n" % implant.minimum_cluster_bright
        blob += "<highlight>%d</highlight> Faded\n" % implant.minimum_cluster_faded

        if implant.ql >= 99:
            blob += "\n<header2>Jobe Requirements</header2>\n"

            blob += "\n<header2>Requirements to Wear</header2>\n"
            blob += "<highlight>%d</highlight> Treatment\n" % implant.jobe_treatment
            blob += "<highlight>%d</highlight> Ability\n" % implant.jobe_ability

            blob += "\n<header2>Max Requirements to Build</header2> (actual requirements may be lower)\n"
            blob += "<highlight>%d</highlight> NanoProgramming for Shiny\n" % implant.jobe_build_shiny
            blob += "<highlight>%d</highlight> NanoProgramming for Bright\n" % implant.jobe_build_bright
            blob += "<highlight>%d</highlight> NanoProgramming for Faded\n" % implant.jobe_build_faded

            blob += "\nJobe implants cannot be cleaned\n"

        blob += "\n\nBased on the !impql command written for %s by <highlight>Lucier</highlight>" % self.text.make_chatcmd("Ttst", "/tell ttst help")

        return blob

    def get_implant_by_ql(self, ql):
        implant = DictObject({})

        implant.ql = ql

        implant.treatment = int(self.util.interpolate_value(ql, self.normal_treatment_req))
        implant.ability = int(self.util.interpolate_value(ql, self.normal_ability_req))

        implant.jobe_treatment = self.util.interpolate_value(ql, self.jobe_treatment_req)
        implant.jobe_ability = self.util.interpolate_value(ql, self.jobe_ability_req)

        implant.ability_shiny = self.util.interpolate_value(ql, self.ability_shiny_bonus)
        implant.ability_shiny_min, implant.ability_shiny_max = self.get_range(ql, implant.ability_shiny, self.ability_shiny_bonus)
        implant.ability_bright = self.util.interpolate_value(ql, self.ability_bright_bonus)
        implant.ability_bright_min, implant.ability_bright_max = self.get_range(ql, implant.ability_bright, self.ability_bright_bonus)
        implant.ability_faded = self.util.interpolate_value(ql, self.ability_faded_bonus)
        implant.ability_faded_min, implant.ability_faded_max = self.get_range(ql, implant.ability_faded, self.ability_faded_bonus)

        implant.skill_shiny = self.util.interpolate_value(ql, self.skill_shiny_bonus)
        implant.skill_shiny_min, implant.skill_shiny_max = self.get_range(ql, implant.skill_shiny, self.skill_shiny_bonus)
        implant.skill_bright = self.util.interpolate_value(ql, self.skill_bright_bonus)
        implant.skill_bright_min, implant.skill_bright_max = self.get_range(ql, implant.skill_bright, self.skill_bright_bonus)
        implant.skill_faded = self.util.interpolate_value(ql, self.skill_faded_bonus)
        implant.skill_faded_min, implant.skill_faded_max = self.get_range(ql, implant.skill_faded, self.skill_faded_bonus)

        implant.clean_break_and_entry = self.util.interpolate_value(ql, self.clean_be)
        implant.clean_nano_programming = self.util.interpolate_value(ql, self.clean_np)

        implant.build_shiny = self.util.interpolate_value(ql, self.normal_build_shiny)
        implant.build_bright = self.util.interpolate_value(ql, self.normal_build_bright)
        implant.build_faded = self.util.interpolate_value(ql, self.normal_build_faded)

        implant.jobe_build_shiny = self.util.interpolate_value(ql, self.jobe_build_shiny)
        implant.jobe_build_bright = self.util.interpolate_value(ql, self.jobe_build_bright)
        implant.jobe_build_faded = self.util.interpolate_value(ql, self.jobe_build_faded)

        if ql >= 201:
            implant.minimum_cluster_shiny = max(201, math.floor(ql * 0.86))
            implant.minimum_cluster_bright = max(201, math.floor(ql * 0.84))
            implant.minimum_cluster_faded = max(201, math.floor(ql * 0.82))
        else:
            implant.minimum_cluster_shiny = math.floor(ql * 0.86)
            implant.minimum_cluster_bright = math.floor(ql * 0.84)
            implant.minimum_cluster_faded = math.floor(ql * 0.82)

        return implant

    def get_range(self, ql, value, interpolation):
        min_ql = ql
        max_ql = ql

        while self.util.interpolate_value(min_ql - 1, interpolation) == value:
            min_ql -= 1

        while self.util.interpolate_value(max_ql + 1, interpolation) == value:
            max_ql += 1

        return [min_ql, max_ql]
