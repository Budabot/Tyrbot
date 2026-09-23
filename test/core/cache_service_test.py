import os
import shutil
import tempfile
import unittest

from core.cache_service import CacheService


class CacheServiceTest(unittest.TestCase):
    """
    These run against a temp directory. They must never touch ./data/cache: that belongs to the
    running bot, and this suite used to delete it outright.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="tyrbot_cache_test_")
        self.cache = CacheService(base_path=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_store_overwrite(self):
        self.cache.store("test", "test.txt", "this is a test")
        contents = self.cache.retrieve("test", "test.txt")

        self.assertEqual("this is a test", contents.data)
        self.cache.store("test", "test.txt", "this is a test2")

        contents = self.cache.retrieve("test", "test.txt")
        self.assertEqual("this is a test2", contents.data)

    def test_retrieve_empty(self):
        contents = self.cache.retrieve("test", "empty.txt")

        self.assertIsNone(contents)

    def test_retrieve_expired(self):
        self.cache.store("test", "test.txt", "this is a test")

        contents = self.cache.retrieve("test", "test.txt")
        self.assertEqual("this is a test", contents.data)

    def test_writes_stay_inside_the_temp_dir(self):
        self.cache.store("test", "test.txt", "this is a test")

        _, full_path = self.cache.get_full_path("test", "test.txt")
        self.assertTrue(os.path.abspath(full_path).startswith(os.path.abspath(self.temp_dir)))
        self.assertTrue(os.path.exists(full_path))

    def test_store_recreates_a_missing_cache_dir(self):
        # the cache dir is created lazily by store(), so it may be absent or deleted under us
        self.cache.store("test", "test.txt", "first")
        shutil.rmtree(os.path.join(self.temp_dir, "data", "cache"))

        self.cache.store("test", "test.txt", "this is a test")

        self.assertEqual("this is a test", self.cache.retrieve("test", "test.txt").data)
