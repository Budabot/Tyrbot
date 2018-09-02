import unittest

from core.dict_object import DictObject
from modules.standard.implant.ladder_controller import LadderController


class LadderControllerTest(unittest.TestCase):

    def test_get_next_grade(self):
        ladder_controller = LadderController()
        grades = ["shiny", "bright", "faded"]

        self.assertEqual("bright", ladder_controller.get_next_grade("shiny", grades))
        self.assertEqual("faded", ladder_controller.get_next_grade("bright", grades))
        self.assertEqual("shiny", ladder_controller.get_next_grade("faded", grades))
        self.assertEqual("shiny", ladder_controller.get_next_grade(None, grades))

    def test_get_cluser_min_ql(self):
        ladder_controller = LadderController()

        self.assertEqual(86, ladder_controller.get_cluser_min_ql(100, "shiny"))
        self.assertEqual(84, ladder_controller.get_cluser_min_ql(100, "bright"))
        self.assertEqual(82, ladder_controller.get_cluser_min_ql(100, "faded"))

        self.assertEqual(201, ladder_controller.get_cluser_min_ql(201, "shiny"))
        self.assertEqual(201, ladder_controller.get_cluser_min_ql(201, "bright"))
        self.assertEqual(201, ladder_controller.get_cluser_min_ql(201, "faded"))

        self.assertEqual(258, ladder_controller.get_cluser_min_ql(300, "shiny"))
        self.assertEqual(252, ladder_controller.get_cluser_min_ql(300, "bright"))
        self.assertEqual(245, ladder_controller.get_cluser_min_ql(300, "faded"))

    def test_calculate_treatment(self):
        ladder_controller = LadderController()

        prefix = "skill_"

        slots = DictObject({"shiny": None,
                            "bright": None,
                            "faded": None})

        self.assertEqual(0, ladder_controller.calculate_total(slots, prefix))

        slots.shiny = {"skill_shiny": 30}
        self.assertEqual(30, ladder_controller.calculate_total(slots, prefix))

        slots.bright = {"skill_bright": 20}
        self.assertEqual(50, ladder_controller.calculate_total(slots, prefix))

        slots.faded = {"skill_faded": 10}
        self.assertEqual(60, ladder_controller.calculate_total(slots, prefix))

        self.assertEqual(30, ladder_controller.calculate_total(slots, prefix, "shiny"))
        self.assertEqual(40, ladder_controller.calculate_total(slots, prefix, "bright"))
        self.assertEqual(50, ladder_controller.calculate_total(slots, prefix, "faded"))
