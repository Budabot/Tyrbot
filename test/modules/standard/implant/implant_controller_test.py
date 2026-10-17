from decimal import Decimal
import unittest
import unittest.mock

from core.dict_object import DictObject
from core.util import Util
from modules.standard.implant.implant_controller import ImplantController

IMPLANT_QLS = (1, 200, 201, 300)

# The game's bonuses at QL 1, 200, 201 and 300 for a cluster of each kind, by its unrounded shiny bonus at QL 200;
# stored values come back from the database as int, float (SQLite) or Decimal (MySQL)
GAME_BONUSES = {
    -5: {"shiny": (5, -5, -5, -9), "bright": (3, -3, -3, -5), "faded": (2, -2, -2, -3)},
    Decimal("-2.5"): {"shiny": (5, -2, -3, -5), "bright": (3, -2, -2, -3), "faded": (2, -1, -1, -2)},
    7: {"shiny": (5, 7, 7, 8), "bright": (3, 4, 4, 5), "faded": (2, 3, 3, 3)},
    15: {"shiny": (5, 15, 15, 19), "bright": (3, 9, 9, 11), "faded": (2, 6, 6, 7)},
    17.5: {"shiny": (5, 18, 18, 22), "bright": (3, 10, 11, 13), "faded": (2, 7, 7, 9)},
    20: {"shiny": (5, 20, 20, 25), "bright": (3, 12, 12, 15), "faded": (2, 8, 8, 10)},
    30: {"shiny": (5, 30, 30, 39), "bright": (3, 18, 18, 23), "faded": (2, 12, 12, 16)},
    55: {"shiny": (5, 55, 55, 73), "bright": (3, 33, 33, 44), "faded": (2, 22, 22, 29)},
    105: {"shiny": (6, 105, 106, 141), "bright": (3, 63, 63, 85), "faded": (2, 42, 42, 57)},
    130: {"shiny": (6, 130, 131, 175), "bright": (3, 78, 78, 105), "faded": (2, 52, 52, 70)},
    405: {"shiny": (7, 405, 407, 550), "bright": (4, 243, 244, 330), "faded": (3, 162, 163, 220)},
    505: {"shiny": (8, 505, 508, 687), "bright": (4, 303, 304, 412), "faded": (3, 202, 203, 275)},
}


# Clusters with the highest normal and Jobe build requirements, and lower ones
CLUSTERS = [
    DictObject({"LongName": "Nano Pool", "NPReq": 1200, "JobeSkill": ""}),
    DictObject({"LongName": "Strength", "NPReq": 900, "JobeSkill": ""}),
    DictObject({"LongName": "Add XP (%)*", "NPReq": 1, "JobeSkill": "Psychology"}),
    DictObject({"LongName": "Nano Delta*", "NPReq": 1, "JobeSkill": "Pharma Tech"}),
]


def make_controller(row):
    controller = ImplantController()
    controller.db = unittest.mock.Mock()
    controller.db.query_single.return_value = row
    return controller


class ClusterBonusTest(unittest.TestCase):
    def test_matches_the_game_at_each_implant_ql(self):
        for shiny_ql200, grades in GAME_BONUSES.items():
            for grade, bonuses in grades.items():
                for ql, bonus in zip(IMPLANT_QLS, bonuses):
                    with self.subTest(shiny_ql200=shiny_ql200, grade=grade, ql=ql):
                        self.assertEqual(bonus, ImplantController.cluster_bonus(shiny_ql200, ql, grade))

    def test_interpolates_between_implant_qls(self):
        # 6 + (105 - 6) * 99 / 199 = 55.25
        self.assertEqual(55, ImplantController.cluster_bonus(105, 100, "shiny"))
        # 63 + (85 - 63) * 49 / 99 = 73.9
        self.assertEqual(74, ImplantController.cluster_bonus(105, 250, "bright"))

    def test_rejects_an_unknown_grade_or_ql(self):
        for args in ((105, 0, "shiny"), (105, 301, "faded"), (105, 100, "shining")):
            with self.subTest(args=args), self.assertRaises(ValueError):
                ImplantController.cluster_bonus(*args)

    def test_get_cluster_bonus_uses_the_clusters_stored_value(self):
        controller = make_controller(DictObject({"ShinyQL200": Decimal("17.5")}))
        self.assertEqual(10, controller.get_cluster_bonus("Add Projectile Damage*", 200, "bright"))
        self.assertEqual(["Add Projectile Damage*"], controller.db.query_single.call_args.args[1])

    def test_get_cluster_bonus_rejects_an_unknown_cluster(self):
        controller = make_controller(None)
        with self.assertRaises(ValueError):
            controller.get_cluster_bonus("No Such Cluster", 200, "shiny")

    def test_bonus_range_spans_the_qls_with_the_same_bonus(self):
        controller = make_controller(None)
        self.assertEqual([1, 3], controller.get_bonus_range(105, 1, "faded", 2))
        self.assertEqual([299, 300], controller.get_bonus_range(105, 300, "shiny", 141))
        self.assertEqual([199, 203], controller.get_bonus_range(55, 200, "shiny", 55))


class ClusterBuildRequirementTest(unittest.TestCase):
    def test_normal_cluster_scales_its_shiny_requirement_at_ql_200(self):
        # 1 Handed Blunt Weapons: 1.8 x QL x 2 / 1.5 / 1
        controller = make_controller(DictObject({"LongName": "1 Handed Blunt Weapons", "NPReq": 720, "JobeSkill": ""}))
        self.assertEqual(("Nano Programming", 360), controller.get_cluster_build_requirement("1 Handed Blunt Weapons", 100, "shiny"))
        self.assertEqual(("Nano Programming", 270), controller.get_cluster_build_requirement("1 Handed Blunt Weapons", 100, "bright"))
        self.assertEqual(("Nano Programming", 180), controller.get_cluster_build_requirement("1 Handed Blunt Weapons", 100, "faded"))
        self.assertEqual(["1 Handed Blunt Weapons"], controller.db.query_single.call_args.args[1])

    def test_rounds_up(self):
        # 860 x 99 / 200 / 2 = 212.85
        controller = make_controller(DictObject({"LongName": "Treatment", "NPReq": 860, "JobeSkill": ""}))
        self.assertEqual(("Nano Programming", 213), controller.get_cluster_build_requirement("Treatment", 99, "faded"))

    def test_jobe_cluster_needs_its_skill_per_ql(self):
        controller = make_controller(DictObject({"LongName": "Add XP (%)*", "NPReq": 1, "JobeSkill": "Psychology"}))
        self.assertEqual(("Psychology", 1250), controller.get_cluster_build_requirement("Add XP (%)*", 200, "shiny"))
        self.assertEqual(("Psychology", 950), controller.get_cluster_build_requirement("Add XP (%)*", 200, "bright"))
        self.assertEqual(("Psychology", 650), controller.get_cluster_build_requirement("Add XP (%)*", 200, "faded"))

    def test_nano_delta_needs_less(self):
        controller = make_controller(DictObject({"LongName": "Nano Delta*", "NPReq": 1, "JobeSkill": "Pharma Tech"}))
        self.assertEqual(("Pharma Tech", 1050), controller.get_cluster_build_requirement("Nano Delta*", 200, "shiny"))
        self.assertEqual(("Pharma Tech", 800), controller.get_cluster_build_requirement("Nano Delta*", 200, "bright"))
        self.assertEqual(("Pharma Tech", 550), controller.get_cluster_build_requirement("Nano Delta*", 200, "faded"))

    def test_refined_implants_have_unknown_requirements(self):
        controller = make_controller(DictObject({"LongName": "1 Handed Blunt Weapons", "NPReq": 720, "JobeSkill": ""}))
        self.assertEqual(("Nano Programming", None), controller.get_cluster_build_requirement("1 Handed Blunt Weapons", 201, "shiny"))

    def test_rejects_an_unknown_cluster_grade_or_ql(self):
        controller = make_controller(DictObject({"LongName": "1 Handed Blunt Weapons", "NPReq": 720, "JobeSkill": ""}))
        for args in (("1 Handed Blunt Weapons", 0, "shiny"), ("1 Handed Blunt Weapons", 301, "shiny"), ("1 Handed Blunt Weapons", 100, "shining")):
            with self.subTest(args=args), self.assertRaises(ValueError):
                controller.get_cluster_build_requirement(*args)
        controller.db.query_single.return_value = None
        with self.assertRaises(ValueError):
            controller.get_cluster_build_requirement("No Such Cluster", 100, "shiny")

    def test_max_build_requirements_are_the_highest_normal_and_jobe_amounts(self):
        controller = make_controller(None)
        controller.db.query.return_value = CLUSTERS

        build = controller.get_max_build_requirements(200)

        self.assertEqual((1200, 900, 600), (build.normal_shiny, build.normal_bright, build.normal_faded))
        self.assertEqual((1250, 950, 650), (build.jobe_shiny, build.jobe_bright, build.jobe_faded))
        self.assertEqual(["Pharma Tech", "Psychology"], build.jobe_skills)

    def test_max_build_requirements_of_refined_implants_are_unknown(self):
        controller = make_controller(None)
        controller.db.query.return_value = CLUSTERS

        build = controller.get_max_build_requirements(201)

        self.assertEqual((None, None), (build.normal_shiny, build.jobe_faded))


class ImplantByQlTest(unittest.TestCase):
    def test_reads_wear_requirements_from_the_table(self):
        requirements = DictObject({"treatment": 951, "ability": 404, "jobe_treatment": 1005, "jobe_ability": 464})
        controller = make_controller(None)
        controller.util = Util()
        controller.db.query.return_value = CLUSTERS
        controller.db.query_single.side_effect = \
            lambda sql, params: requirements if "implant_requirement" in sql else DictObject({"ShinyQL200": 105})

        implant = controller.get_implant_by_ql(200)

        self.assertEqual((951, 404, 1005, 464), (implant.treatment, implant.ability, implant.jobe_treatment, implant.jobe_ability))

    def test_rejects_a_ql_without_wear_requirements(self):
        controller = make_controller(None)
        with self.assertRaises(ValueError):
            controller.get_implant_by_ql(200)
