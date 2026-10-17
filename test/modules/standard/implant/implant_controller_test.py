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


class ImplantByQlTest(unittest.TestCase):
    def test_reads_wear_requirements_from_the_table(self):
        requirements = DictObject({"treatment": 951, "ability": 404, "jobe_treatment": 1005, "jobe_ability": 464})
        controller = make_controller(None)
        controller.util = Util()
        controller.db.query_single.side_effect = \
            lambda sql, params: requirements if "implant_requirement" in sql else DictObject({"ShinyQL200": 105})

        implant = controller.get_implant_by_ql(200)

        self.assertEqual((951, 404, 1005, 464), (implant.treatment, implant.ability, implant.jobe_treatment, implant.jobe_ability))

    def test_rejects_a_ql_without_wear_requirements(self):
        controller = make_controller(None)
        with self.assertRaises(ValueError):
            controller.get_implant_by_ql(200)
