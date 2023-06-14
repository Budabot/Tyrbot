import unittest

from core.dict_object import DictObject


class DictObjectTest(unittest.TestCase):

    def test_access(self):
        d = DictObject({"test1": 2, "test2": 2})
        self.assertEqual(2, d["test1"])
        self.assertEqual(2, d.test2)

    def test_update(self):
        d = DictObject({"test1": 2, "test2": 2})
        d["test1"] = 3
        d.test2 = 4
        self.assertEqual(3, d["test1"])
        self.assertEqual(3, d.test1)
        self.assertEqual(4, d["test2"])
        self.assertEqual(4, d.test2)

    def test_to_string(self):
        d = DictObject({"test1": 1})
        self.assertEqual("{'test1': 1}", str(d))

    def test_nested_access(self):
        d = DictObject({"test1": {"test2": 2}})
        self.assertEqual(2, d["test1"]["test2"])
        self.assertEqual(2, d.test1.test2)

    def test_nested_dict_update(self):
        d = DictObject({"test1": {"test2": 2}})
        d["test1"]["test2"] = 3
        self.assertEqual(3, d.test1.test2)
        self.assertEqual(3, d["test1"]["test2"])

    def test_nested_property_update(self):
        d = DictObject({"test1": {"test2": 2}})
        d.test1.test2 = 3
        self.assertEqual(3, d.test1.test2)
        self.assertEqual(3, d["test1"]["test2"])

    def test_nested_to_string(self):
        d = DictObject({"test1": {"test2": 2}})
        self.assertEqual("{'test1': {'test2': 2}}", str(d))

    def test_empty_access(self):
        d = DictObject()
        self.assertRaises(KeyError, lambda: d["test1"])
        self.assertRaises(AttributeError, lambda: d.test1)

    def test_empty_update(self):
        d = DictObject()
        d["test1"] = 1
        d.test2 = 2
        self.assertEqual(1, d["test1"])
        self.assertEqual(1, d.test1)
        self.assertEqual(2, d["test2"])
        self.assertEqual(2, d.test2)

    def test_len(self):
        d = DictObject()
        self.assertEqual(0, len(d))
        d["test1"] = 1
        self.assertEqual(1, len(d))
        d.test2 = 2
        self.assertEqual(2, len(d))
        d["test2"] = 3
        self.assertEqual(2, len(d))

    def test_nested_arrays(self):
        d = DictObject({"users": [{"id": 1}, {"id": 2}, None]})
        self.assertEqual(d.users, [{"id": 1}, {"id": 2}, None])
        self.assertEqual(d.users[0], {"id": 1})
        self.assertEqual(d.users[0].id, 1)
        self.assertEqual(d.users[2], None)
