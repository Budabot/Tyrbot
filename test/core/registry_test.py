import unittest

from core.registry import Registry


class RegistryTest(unittest.TestCase):

    def test_format_name(self):
        self.assertEqual("test_controller", Registry.format_name("TestController"))
        self.assertEqual("test_things_controller", Registry.format_name("TestThingsController"))
        self.assertEqual("test12_controller", Registry.format_name("Test12Controller"))

