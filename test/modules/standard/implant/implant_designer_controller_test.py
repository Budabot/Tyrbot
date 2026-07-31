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

    def test_get_cluster_min_ql(self):
        self.assertEqual(172, self.controller.get_cluster_min_ql(200, "shiny"))
        self.assertEqual(168, self.controller.get_cluster_min_ql(200, "bright"))
        self.assertEqual(164, self.controller.get_cluster_min_ql(200, "faded"))
        self.assertEqual(215, self.controller.get_cluster_min_ql(250, "shiny"))
