import unittest
from unittest.mock import MagicMock, patch

from core.dict_object import DictObject
from modules.standard.implant.implant_designer_controller import ImplantDesignerController


class ImplantDesignerControllerTest(unittest.TestCase):

    def setUp(self):
        self.controller = ImplantDesignerController()
        self.controller.db = MagicMock()
        self.controller.text = MagicMock()
        self.controller.util = MagicMock()
        self.controller.command_alias_service = MagicMock()
        self.controller.implant_controller = MagicMock()
        self.controller.implant_controller.NP_SKILL = "Nano Programming"

        self.controller.text.make_tellcmd = lambda label, cmd: f"[{label}]({cmd})"

    def test_implantdesigner_clear_cmd(self):
        request = DictObject({"sender": DictObject({"name": "Testuser"})})

        self.controller.db.query_single.return_value = None

        result = self.controller.implantdesigner_clear_cmd(request, "clear")
        self.assertIsNotNone(result)
        self.assertIn("Implant Designer has been cleared.", result.msg)

    def test_handle_add_cluster_or_symb(self):
        self.controller.db.query_single.return_value = None

        result = self.controller.handle_add_cluster_or_symb("Testuser", "head", "shiny", "Nano Pool")
        self.assertIn("head(shiny)", result.msg)
        self.assertIn("Nano Pool", result.msg)

    def test_build_requirements_keep_the_highest_of_each_skill(self):
        amounts = {("Max Health", "shiny"): ("Nano Programming", 500), ("Add XP (%)*", "bright"): ("Psychology", 475),
                   ("Strength", "faded"): ("Nano Programming", 113)}
        self.controller.implant_controller.get_cluster_build_requirement.side_effect = lambda name, ql, grade: amounts[(name, grade)]
        slot_obj = DictObject({"ql": 100, "shiny": "Max Health", "bright": "Add XP (%)*", "faded": "Strength"})

        reqs = self.controller.get_build_requirements(100, slot_obj)

        self.assertEqual({"Nano Programming": 500, "Psychology": 475}, reqs)
        self.assertEqual("Nano Programming: 500, Psychology: 475", self.controller.format_build_requirements(reqs))

    def test_an_unknown_amount_makes_the_skill_unknown(self):
        reqs = {}
        self.controller.add_build_requirement(reqs, "Nano Programming", 800)
        self.controller.add_build_requirement(reqs, "Nano Programming", None)
        self.controller.add_build_requirement(reqs, "Nano Programming", 900)
        self.assertEqual({"Nano Programming": None}, reqs)
        self.assertEqual("Nano Programming: unknown", self.controller.format_build_requirements(reqs))

    def test_get_cluster_min_ql(self):
        self.assertEqual(172, self.controller.get_cluster_min_ql(200, "shiny"))
        self.assertEqual(168, self.controller.get_cluster_min_ql(200, "bright"))
        self.assertEqual(164, self.controller.get_cluster_min_ql(200, "faded"))
        self.assertEqual(215, self.controller.get_cluster_min_ql(250, "shiny"))
