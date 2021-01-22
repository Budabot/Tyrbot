from core.registry import Registry
from core.setting_types import BooleanSettingType
import unittest


class MockSettingService:
    def __init__(self):
        self.vals = {}

    def set_value(self, name, value):
        self.vals[name] = value

    def get_value(self, name):
        return self.vals[name]


class SettingTypesTest(unittest.TestCase):
    def test_boolean_setting_type(self):
        Registry.clear()
        Registry.add_instance("setting_service", MockSettingService())
        setting = BooleanSettingType()

        setting.set_value("true")
        self.assertTrue(setting.get_value())

        setting.set_value(True)
        self.assertTrue(setting.get_value())

        setting.set_value("false")
        self.assertFalse(setting.get_value())

        setting.set_value(False)
        self.assertFalse(setting.get_value())

        self.assertRaises(Exception, lambda: setting.set_value("test"))
