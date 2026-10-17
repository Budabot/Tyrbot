from fractions import Fraction
import math

from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.command_param_types import Any, Const, Int
from core.dict_object import DictObject


@instance()
class ImplantController:
    # Each cluster grade's share of the shiny bonus
    GRADE_RATIOS = {"shiny": Fraction(1), "bright": Fraction(3, 5), "faded": Fraction(2, 5)}
    # Clusters whose bonuses stand for all ability and all skill clusters
    ABILITY_CLUSTER = "Strength"
    SKILL_CLUSTER = "Assault Rifle"
    # Skill that adds normal clusters, and each grade's share of a cluster's shiny requirement
    NP_SKILL = "Nano Programming"
    NP_GRADE_RATIOS = {"shiny": Fraction(1), "bright": Fraction(3, 4), "faded": Fraction(1, 2)}
    # Skill per implant QL that adds a Jobe cluster of each grade; Nano Delta clusters need less
    JOBE_SKILL_RATIOS = {"shiny": Fraction(25, 4), "bright": Fraction(19, 4), "faded": Fraction(13, 4)}
    NANO_DELTA_CLUSTER = "Nano Delta*"
    NANO_DELTA_SKILL_RATIOS = {"shiny": Fraction(21, 4), "bright": Fraction(4), "faded": Fraction(11, 4)}
    # Highest QL whose build requirements are known
    BUILD_REQUIREMENT_MAX_QL = 200

    def __init__(self):
        self.grades = ["shiny", "bright", "faded"]

        self.clean_np = {1: 1, 200: 200}
        self.clean_be = {1: 4, 200: 950}

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.text = registry.get_instance("text")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def pre_start(self):
        self.db.load_sql_file(self.module_dir + "/sql/" + "Ability.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "Cluster.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "ClusterBonus.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "ClusterImplantMap.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "ClusterType.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "ImplantMatrix.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "ImplantType.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "Profession.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "Symbiant.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "SymbiantAbilityMatrix.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "SymbiantClusterMatrix.sql")
        self.db.load_sql_file(self.module_dir + "/sql/" + "SymbiantProfessionMatrix.sql")

        self.db.load_sql_file(self.module_dir + "/sql/" + "implant_requirements.sql")

    def start(self):
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

        if implant.ql <= 200:
            blob += "\n<header2>Requirements to Clean</header2>\n"
            blob += "<highlight>%d</highlight> Break&Entry\n" % implant.clean_break_and_entry
            blob += "<highlight>%d</highlight> NanoProgramming\n" % implant.clean_nano_programming
        else:
            blob += "\nRefined implants cannot be cleaned\n"

        if implant.build_shiny is None:
            blob += "\nBuild requirements of refined implants are unknown\n"
        else:
            blob += "\n<header2>Max Requirements to Build</header2> (actual requirements may be lower)\n"
            blob += "<highlight>%d</highlight> NanoProgramming for Shiny\n" % implant.build_shiny
            blob += "<highlight>%d</highlight> NanoProgramming for Bright\n" % implant.build_bright
            blob += "<highlight>%d</highlight> NanoProgramming for Faded\n" % implant.build_faded

        blob += "\n<header2>Min Cluster QL</header2>\n"
        blob += "<highlight>%d</highlight> Shiny\n" % implant.minimum_cluster_shiny
        blob += "<highlight>%d</highlight> Bright\n" % implant.minimum_cluster_bright
        blob += "<highlight>%d</highlight> Faded\n" % implant.minimum_cluster_faded

        if implant.ql >= 99:
            blob += "\n<header2>Max Requirements to Wear Jobe Implants</header2> (actual requirements may be lower)\n"
            blob += "<highlight>%d</highlight> Treatment\n" % implant.jobe_treatment
            blob += "<highlight>%d</highlight> Ability\n" % implant.jobe_ability

            if implant.jobe_build_shiny is None:
                blob += "\nBuild requirements of refined Jobe implants are unknown\n"
            else:
                blob += "\n<header2>Max Requirements to Build Jobe Implants</header2> (actual requirements may be lower)\n"
                blob += "<highlight>%d</highlight> for Shiny\n" % implant.jobe_build_shiny
                blob += "<highlight>%d</highlight> for Bright\n" % implant.jobe_build_bright
                blob += "<highlight>%d</highlight> for Faded\n" % implant.jobe_build_faded
                skills = implant.jobe_build_skills
                blob += "in the Jobe cluster's tradeskill: %s\n" % (" or ".join([", ".join(skills[:-1]), skills[-1]]) if len(skills) > 1 else skills[0])

            blob += "\nJobe implants cannot be cleaned\n"

        blob += "\n\nBased on the !impql command written for %s by <highlight>Lucier</highlight>" % self.text.make_chatcmd("Ttst", "/tell ttst help")

        return blob

    def get_implant_by_ql(self, ql):
        implant = DictObject({})

        implant.ql = ql

        # Wear requirements of normal implants, and the highest of Jobe implants
        row = self.db.query_single("SELECT treatment, ability, jobe_treatment, jobe_ability FROM implant_requirement WHERE ql = ?", [ql])
        if not row:
            raise ValueError(f"Implant QL {ql} has no wear requirements in implant_requirement")
        implant.treatment = row.treatment
        implant.ability = row.ability
        implant.jobe_treatment = row.jobe_treatment
        implant.jobe_ability = row.jobe_ability

        # Bonus of each grade, and the QLs that give the same bonus, for ability and skill clusters
        for kind, cluster_name in (("ability", self.ABILITY_CLUSTER), ("skill", self.SKILL_CLUSTER)):
            shiny_ql200 = self.get_cluster_shiny_ql200(cluster_name)
            for grade in self.grades:
                bonus = self.cluster_bonus(shiny_ql200, ql, grade)
                implant[f"{kind}_{grade}"] = bonus
                implant[f"{kind}_{grade}_min"], implant[f"{kind}_{grade}_max"] = self.get_bonus_range(shiny_ql200, ql, grade, bonus)

        implant.clean_break_and_entry = self.util.interpolate_value(ql, self.clean_be)
        implant.clean_nano_programming = self.util.interpolate_value(ql, self.clean_np)

        # Highest Nano Programming that normal clusters need, and highest skill that Jobe clusters need
        build = self.get_max_build_requirements(ql)
        for grade in self.grades:
            implant[f"build_{grade}"] = build[f"normal_{grade}"]
            implant[f"jobe_build_{grade}"] = build[f"jobe_{grade}"]
        implant.jobe_build_skills = build.jobe_skills

        if ql >= 201:
            implant.minimum_cluster_shiny = max(201, math.floor(ql * 0.86))
            implant.minimum_cluster_bright = max(201, math.floor(ql * 0.84))
            implant.minimum_cluster_faded = max(201, math.floor(ql * 0.82))
        else:
            implant.minimum_cluster_shiny = math.floor(ql * 0.86)
            implant.minimum_cluster_bright = math.floor(ql * 0.84)
            implant.minimum_cluster_faded = math.floor(ql * 0.82)

        return implant

    def get_bonus_range(self, shiny_ql200, ql, grade, bonus):
        min_ql = ql
        while min_ql > 1 and self.cluster_bonus(shiny_ql200, min_ql - 1, grade) == bonus:
            min_ql -= 1

        max_ql = ql
        while max_ql < 300 and self.cluster_bonus(shiny_ql200, max_ql + 1, grade) == bonus:
            max_ql += 1

        return [min_ql, max_ql]

    def get_cluster_shiny_ql200(self, cluster_name):
        row = self.db.query_single("SELECT b.ShinyQL200 FROM ClusterBonus b JOIN Cluster c ON b.ClusterID = c.ClusterID WHERE c.LongName = ?",
                                   [cluster_name])
        if not row:
            raise ValueError(f"Cluster '{cluster_name}' has no bonus in ClusterBonus")
        return row.ShinyQL200

    def get_cluster_bonus(self, cluster_name, ql, grade):
        return self.cluster_bonus(self.get_cluster_shiny_ql200(cluster_name), ql, grade)

    def get_cluster_build_requirement(self, cluster_name, ql, grade):
        row = self.db.query_single("SELECT LongName, NPReq, JobeSkill FROM Cluster WHERE LongName = ?", [cluster_name])
        if not row:
            raise ValueError(f"Cluster '{cluster_name}' is not in Cluster")
        return self.build_requirement(row, ql, grade)

    def get_max_build_requirements(self, ql):
        # Highest amount of each grade that any normal and any Jobe cluster needs for an implant of the given QL, None when
        # unknown, and the skills Jobe clusters need
        clusters = self.db.query("SELECT LongName, NPReq, JobeSkill FROM Cluster WHERE ClusterID != 0")
        maximums = DictObject({"jobe_skills": sorted({c.JobeSkill for c in clusters if c.JobeSkill})})
        for kind, is_jobe in (("normal", False), ("jobe", True)):
            for grade in self.grades:
                amounts = [self.build_requirement(c, ql, grade)[1] for c in clusters if bool(c.JobeSkill) == is_jobe]
                if not amounts:
                    raise ValueError(f"Cluster has no {kind} clusters")
                maximums[f"{kind}_{grade}"] = None if None in amounts else max(amounts)
        return maximums

    def build_requirement(self, cluster, ql, grade):
        # Skill needed to add a cluster to an implant of the given QL, and the amount rounded up, or None above the known QLs;
        # normal clusters scale their shiny Nano Programming requirement at QL 200, Jobe clusters need another skill per QL
        if grade not in self.NP_GRADE_RATIOS:
            raise ValueError(f"Unknown cluster grade '{grade}'")
        if not 1 <= ql <= 300:
            raise ValueError(f"Implant QL {ql} is not between 1 and 300")

        if cluster.JobeSkill:
            ratios = self.NANO_DELTA_SKILL_RATIOS if cluster.LongName == self.NANO_DELTA_CLUSTER else self.JOBE_SKILL_RATIOS
            skill, amount = cluster.JobeSkill, ratios[grade] * ql
        else:
            skill, amount = self.NP_SKILL, Fraction(cluster.NPReq) * ql / 200 * self.NP_GRADE_RATIOS[grade]
        return skill, (math.ceil(amount) if ql <= self.BUILD_REQUIREMENT_MAX_QL else None)

    @staticmethod
    def cluster_bonus(shiny_ql200, ql: int, grade: str) -> int:
        # A cluster's bonus, from its unrounded shiny bonus at QL 200; the bonuses at QL 1, 200, 201 and 300 are interpolated
        # in between, and every value is rounded half to even
        if grade not in ImplantController.GRADE_RATIOS:
            raise ValueError(f"Unknown cluster grade '{grade}'")
        if not 1 <= ql <= 300:
            raise ValueError(f"Implant QL {ql} is not between 1 and 300")

        # Unrounded shiny bonus: rises linearly from 5 at QL 0, and at QL 300 by 15/11 of its rise at QL 200
        rise = Fraction(shiny_ql200) - 5
        ratio = ImplantController.GRADE_RATIOS[grade]

        def endpoint(endpoint_ql: int) -> int:
            scale = Fraction(15, 11) if endpoint_ql == 300 else Fraction(endpoint_ql, 200)
            return round((5 + rise * scale) * ratio)

        low, high = (1, 200) if ql <= 200 else (201, 300)
        low_value, high_value = endpoint(low), endpoint(high)
        return round(low_value + Fraction(high_value - low_value) * (ql - low) / (high - low))
