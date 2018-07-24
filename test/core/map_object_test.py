import unittest

from core.map_object import MapObject


class MapObjectTest(unittest.TestCase):

    def test_access(self):
        d = MapObject({"test1": 2, "test2": 2})
        self.assertEqual(2, d["test1"])
        self.assertEqual(2, d.test2)

    def test_update(self):
        d = MapObject({"test1": 2, "test2": 2})
        d["test1"] = 3
        d.test2 = 4
        self.assertEqual(3, d["test1"])
        self.assertEqual(3, d.test1)
        self.assertEqual(4, d["test2"])
        self.assertEqual(4, d.test2)

    def test_to_string(self):
        d = MapObject({"test1": 1})
        self.assertEqual("{'test1': 1}", str(d))

    def test_nested_access(self):
        d = MapObject({"test1": {"test2": 2}})
        self.assertEqual(2, d["test1"]["test2"])
        self.assertEqual(2, d.test1.test2)

    def test_nested_dict_update(self):
        d = MapObject({"test1": {"test2": 2}})
        d["test1"]["test2"] = 3
        self.assertEqual(3, d.test1.test2)
        self.assertEqual(3, d["test1"]["test2"])

    def test_nested_property_update(self):
        d = MapObject({"test1": {"test2": 2}})
        d.test1.test2 = 3
        self.assertEqual(3, d.test1.test2)
        self.assertEqual(3, d["test1"]["test2"])

    def test_nested_to_string(self):
        d = MapObject({"test1": {"test2": 2}})
        self.assertEqual("{'test1': {'test2': 2}}", str(d))

    def test_empty_access(self):
        d = MapObject()
        self.assertRaises(KeyError, lambda: d["test1"])
        self.assertRaises(KeyError, lambda: d.test1)

    def test_empty_update(self):
        d = MapObject()
        d["test1"] = 1
        d.test2 = 2
        self.assertEqual(1, d["test1"])
        self.assertEqual(1, d.test1)
        self.assertEqual(2, d["test2"])
        self.assertEqual(2, d.test2)
