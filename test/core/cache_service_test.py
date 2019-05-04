import shutil
import unittest
import time

from core.cache_service import CacheService


class CacheServiceTest(unittest.TestCase):

    def test_store_overwrite(self):
        cache = CacheService()
        cache.store("test", "test.txt", "this is a test")
        contents = cache.retrieve("test", "test.txt")

        self.assertEqual("this is a test", contents.data)
        cache.store("test", "test.txt", "this is a test2")

        contents = cache.retrieve("test", "test.txt")
        self.assertEqual("this is a test2", contents.data)

        # cleanup files
        shutil.rmtree("./data")

    def test_retrieve_empty(self):
        cache = CacheService()
        contents = cache.retrieve("test", "empty.txt")

        self.assertIsNone(contents)

    def test_retrieve_expired(self):
        cache = CacheService()
        cache.store("test", "test.txt", "this is a test")

        contents = cache.retrieve("test", "test.txt")
        self.assertEqual("this is a test", contents.data)

        # cleanup files
        shutil.rmtree("./data")
