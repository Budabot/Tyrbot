import asyncio
import unittest
from unittest.mock import MagicMock

from core.async_service import AsyncService
from core.conn import Conn


class AsyncServiceTest(unittest.TestCase):

    def setUp(self):
        self.async_service = AsyncService()
        self.async_service.start_loop()

    def tearDown(self):
        self.async_service.stop_loop()

    def test_async_service_coroutine_execution(self):
        async def sample_coro():
            await asyncio.sleep(0.01)
            return "hello_async"

        result = self.async_service.run_until_complete(sample_coro(), timeout=5)
        self.assertEqual("hello_async", result)

    def test_conn_initialization(self):
        failure_cb = MagicMock()
        conn = Conn("test_conn", failure_cb, self.async_service)
        self.assertEqual("test_conn", conn.id)
        self.assertIsNone(conn.reader)
        self.assertIsNone(conn.writer)
