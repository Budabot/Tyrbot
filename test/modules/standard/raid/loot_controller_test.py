import unittest
from unittest.mock import MagicMock
from core.registry import Registry

# Mock Registry before importing modules that use decorators which access it at load time
Registry.get_instance = MagicMock()

from modules.standard.raid.loot_controller import LootController
from core.conn import Conn
from core.dict_object import DictObject

class LootControllerTest(unittest.TestCase):
    def setUp(self):
        self.registry = MagicMock()
        self.bot = MagicMock()
        self.db = MagicMock()
        self.text = MagicMock()
        self.leader_controller = MagicMock()
        self.setting_service = MagicMock()
        self.items_controller = MagicMock()
        self.raid_controller = MagicMock()
        
        self.registry.get_instance.side_effect = self._get_instance

        self.loot_controller = LootController()
        self.loot_controller.inject(self.registry)
        
        self.conn = MagicMock()
        self.conn.id = "test_conn"
        
    def _get_instance(self, name):
        if name == "bot": return self.bot
        elif name == "db": return self.db
        elif name == "text": return self.text
        elif name == "leader_controller": return self.leader_controller
        elif name == "setting_service": return self.setting_service
        elif name == "items_controller": return self.items_controller
        elif name == "raid_controller": return self.raid_controller
        return None

    def test_add_item_to_loot_string(self):
        item_name = "test item"
        loot_item = self.loot_controller.add_item_to_loot(item_name, None, 1, self.conn)
        self.assertIsNotNone(loot_item)
        self.assertEqual(loot_item.item, item_name)
        self.assertEqual(loot_item.count, 1)

    def test_add_item_to_loot_dict_object(self):
        item_obj = DictObject({"high_id": 123, "low_id": 123, "ql": 300, "name": "obj item", "icon": 0})
        loot_item = self.loot_controller.add_item_to_loot(item_obj, None, 1, self.conn)
        self.assertIsNotNone(loot_item)
        self.assertEqual(loot_item.item, item_obj)

    def test_add_item_mixed_types_comparison(self):
        self.loot_controller.add_item_to_loot("Custom item", None, 1, self.conn)
        item_obj = DictObject({"high_id": 123, "low_id": 123, "ql": 300, "name": "obj item", "icon": 0})
        self.loot_controller.add_item_to_loot(item_obj, None, 1, self.conn)
        
        loot_list = self.loot_controller.get_loot_list(self.conn)
        self.assertEqual(len(loot_list), 2)
        
        self.loot_controller.add_item_to_loot("Custom item", None, 2, self.conn)
        self.assertEqual(len(loot_list), 2)
        self.assertEqual(loot_list[1].count, 3)
        
        item_obj_duplicate = DictObject({"high_id": 123, "low_id": 123, "ql": 300, "name": "obj item", "icon": 0})
        self.loot_controller.add_item_to_loot(item_obj_duplicate, None, 2, self.conn)
        self.assertEqual(len(loot_list), 2)
        self.assertEqual(loot_list[2].count, 3)

    def test_loot_rem_item_cmd(self):
        self.leader_controller.can_use_command.return_value = True
        self.loot_controller.add_item_to_loot("Custom item", None, 1, self.conn)
        request = MagicMock()
        request.conn = self.conn
        request.sender.char_id = 1234
        
        self.loot_controller.loot_rem_item_cmd(request, None, 1)
        loot_list = self.loot_controller.get_loot_list(self.conn)
        self.assertEqual(len(loot_list), 0)

    def test_loot_rem_item_cmd_missing(self):
        self.leader_controller.can_use_command.return_value = True
        request = MagicMock()
        request.conn = self.conn
        request.sender.char_id = 1234
        
        result = self.loot_controller.loot_rem_item_cmd(request, None, 99)
        self.assertEqual(result, "Loot list is empty.")
        
        self.loot_controller.add_item_to_loot("Custom item", None, 1, self.conn)
        result = self.loot_controller.loot_rem_item_cmd(request, None, 99)
        self.assertEqual(result, "No item at index <highlight>99</highlight> exists.")

    def test_loot_add_item_cmd_security(self):
        self.leader_controller.can_use_command.return_value = True
        request = MagicMock()
        request.conn = self.conn
        request.sender.char_id = 1234
        
        result = self.loot_controller.loot_add_item_cmd(request, None, "rem", 1)
        self.assertTrue(result.startswith("Invalid command syntax"))
        
        result = self.loot_controller.loot_add_item_cmd(request, None, "a" * 101, 1)
        self.assertEqual(result, "Item name is too long (max 100 characters).")
        
        result = self.loot_controller.loot_add_item_cmd(request, None, "item\nnewline", 1)
        self.assertEqual(result, "Item name cannot contain newline characters.")

if __name__ == '__main__':
    unittest.main()
